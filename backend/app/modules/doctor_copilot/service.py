import time
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from app.core.config import settings

from app.modules.audit.models import AuditLog
from app.modules.doctor_copilot.models import CopilotSession, CopilotMessage, CopilotFeedback
from app.modules.doctor_copilot.schemas import (
    CopilotFeedbackCreate,
    CopilotFeedbackResponse,
    CopilotMessageResponse,
    CopilotQueryRequest,
    CopilotSessionCreate,
    CopilotSessionResponse,
    EvidenceItem,
    QueryType,
    SafetyStatus,
    StructuredCopilotResponse,
)
from app.modules.doctor_copilot.context.context_builder import ClinicalContextBuilder
from app.modules.doctor_copilot.retrieval.relevance import classify_query
from app.modules.doctor_copilot.retrieval.evidence_retriever import EvidenceRetriever
from app.modules.doctor_copilot.retrieval.provenance import format_evidence_drilldown
from app.modules.doctor_copilot.prompts.system_prompt import CDSS_SYSTEM_PROMPT, PROMPT_VERSION
from app.modules.doctor_copilot.prompts.clinical_summary_prompt import build_clinical_summary_prompt
from app.modules.doctor_copilot.prompts.question_answer_prompt import build_question_answer_prompt
from app.modules.doctor_copilot.prompts.comparison_prompt import build_comparison_prompt
from app.modules.doctor_copilot.safety.prohibited_requests import is_prohibited_request, build_prohibited_refusal
from app.modules.doctor_copilot.safety.safety_validator import CopilotSafetyValidator
from app.modules.doctor_copilot.llm.provider import (
    BaseCopilotLLMProvider,
    DeterministicCopilotEngine,
    MockCopilotLLMProvider,
)

logger = logging.getLogger("nidan_ai.doctor_copilot.service")


class DoctorCopilotService:
    """
    Main Orchestrator Service for NIDAN AI Doctor Copilot.
    """

    def __init__(self, llm_provider: Optional[BaseCopilotLLMProvider] = None):
        self.context_builder = ClinicalContextBuilder()
        self.evidence_retriever = EvidenceRetriever()
        self.safety_validator = CopilotSafetyValidator()
        self.llm_provider = llm_provider or DeterministicCopilotEngine()

    async def create_session(
        self,
        db: AsyncSession,
        patient_id: str,
        clinician_id: str,
        payload: CopilotSessionCreate,
    ) -> CopilotSession:
        session = CopilotSession(
            patient_id=patient_id,
            clinician_id=clinician_id,
            title=payload.title or "Clinical Case Review",
            status="ACTIVE",
            context_version="1.0",
        )
        db.add(session)
        await db.flush()

        # Audit event
        db.add(
            AuditLog(
                actor_id=clinician_id,
                action="COPILOT_SESSION_CREATED",
                resource_type="COPILOT_SESSION",
                resource_id=session.id,
                details={"patient_id": patient_id, "title": session.title},
            )
        )
        await db.commit()
        await db.refresh(session)
        return session

    async def list_sessions(
        self,
        db: AsyncSession,
        patient_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CopilotSessionResponse]:
        stmt = (
            select(CopilotSession)
            .where(CopilotSession.patient_id == patient_id)
            .order_by(desc(CopilotSession.created_at))
            .offset(offset)
            .limit(limit)
        )
        res = await db.execute(stmt)
        sessions = res.scalars().all()

        responses = []
        for s in sessions:
            # Count messages
            count_stmt = select(func.count(CopilotMessage.id)).where(CopilotMessage.session_id == s.id)
            count_res = await db.execute(count_stmt)
            msg_count = count_res.scalar_one()

            responses.append(
                CopilotSessionResponse(
                    id=s.id,
                    patient_id=s.patient_id,
                    clinician_id=s.clinician_id,
                    title=s.title,
                    status=s.status,
                    context_version=s.context_version,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    message_count=msg_count,
                )
            )
        return responses

    async def get_session(
        self, db: AsyncSession, session_id: str
    ) -> CopilotSession:
        stmt = (
            select(CopilotSession)
            .options(selectinload(CopilotSession.messages))
            .where(CopilotSession.id == session_id)
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Copilot session not found.",
            )
        return session



    async def query_copilot(
        self,
        db: AsyncSession,
        patient_id: str,
        clinician_id: str,
        payload: CopilotQueryRequest,
    ) -> StructuredCopilotResponse:
        start_time = time.time()
        query = payload.query.strip()

        # 1. Prohibited Request Pre-Screening
        is_proh, reason = is_prohibited_request(query)
        if is_proh and reason:
            refusal_resp = build_prohibited_refusal(query, reason)
            
            # Persist message if session_id is given
            if payload.session_id:
                msg = CopilotMessage(
                    session_id=payload.session_id,
                    patient_id=patient_id,
                    role="assistant",
                    content=refusal_resp.answer,
                    query_type=refusal_resp.query_type.value,
                    structured_response=refusal_resp.model_dump(),
                    evidence_ids=[],
                    safety_status=SafetyStatus.PROHIBITED_REQUEST.value,
                    model_provider="nidan-deterministic",
                    model_version="1.0",
                    prompt_version="1.0",
                    safety_version="1.0",
                    response_latency_ms=int((time.time() - start_time) * 1000),
                )
                db.add(msg)

            # Audit log
            db.add(
                AuditLog(
                    actor_id=clinician_id,
                    action="COPILOT_RESPONSE_BLOCKED",
                    resource_type="PATIENT",
                    resource_id=patient_id,
                    details={"reason": reason, "query_type": "PROHIBITED_CLINICAL_DECISION"},
                )
            )
            await db.commit()
            return refusal_resp

        # 2. Build Bounded Patient Context
        patient_context = await self.context_builder.build(db, patient_id)

        # 3. Classify Query
        query_type = classify_query(query)

        # 4. Retrieve Relevant Evidence Items
        relevant_evidence = self.evidence_retriever.retrieve(
            query=query,
            query_type=query_type,
            context=patient_context,
            max_evidence=20,
        )

        # 5. Build Appropriate Prompt
        if query_type == QueryType.PATIENT_SUMMARY:
            user_prompt = build_clinical_summary_prompt(patient_context, relevant_evidence)
        elif query_type == QueryType.LAB_COMPARISON:
            user_prompt = build_comparison_prompt(query, patient_context, relevant_evidence)
        else:
            user_prompt = build_question_answer_prompt(query, patient_context, relevant_evidence)

        # 6. Generate Response via LLM / Deterministic Engine
        raw_response = await self.llm_provider.generate_response(
            system_prompt=CDSS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            query_type=query_type,
            evidence_items=relevant_evidence,
            patient_context=patient_context,
        )

        # Populate context records counts
        raw_response.records_considered = patient_context.get("meta", {}).get("records_considered", 0)
        raw_response.records_included = len(relevant_evidence)
        raw_response.records_excluded = patient_context.get("meta", {}).get("records_excluded", 0)

        # 7. Validate through Master CDSS Safety Validator
        validated_response = self.safety_validator.validate_response(
            response=raw_response,
            evidence_catalog=patient_context.get("evidence_catalog", {}),
            patient_context=patient_context,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # 8. Persist User and Assistant Messages in Session if Provided
        if payload.session_id:
            # User message
            user_msg = CopilotMessage(
                session_id=payload.session_id,
                patient_id=patient_id,
                role="user",
                content=query,
                query_type=query_type.value,
                structured_response={},
                evidence_ids=[],
                safety_status="PASSED",
                model_provider="user",
                model_version="1.0",
                prompt_version="1.0",
                safety_version="1.0",
            )
            db.add(user_msg)

            # Assistant message
            assistant_msg = CopilotMessage(
                session_id=payload.session_id,
                patient_id=patient_id,
                role="assistant",
                content=validated_response.answer,
                query_type=query_type.value,
                structured_response=validated_response.model_dump(),
                evidence_ids=[e.evidence_id for e in relevant_evidence],
                safety_status=validated_response.safety_status.value,
                model_provider=validated_response.model_provider,
                model_version=validated_response.model_version,
                prompt_version=validated_response.prompt_version,
                safety_version=validated_response.safety_version,
                response_latency_ms=latency_ms,
            )
            db.add(assistant_msg)

        # Audit logs
        db.add(
            AuditLog(
                actor_id=clinician_id,
                action="COPILOT_QUERY_SUBMITTED",
                resource_type="PATIENT",
                resource_id=patient_id,
                details={"query_type": query_type.value, "session_id": payload.session_id},
            )
        )
        db.add(
            AuditLog(
                actor_id=clinician_id,
                action="COPILOT_RESPONSE_GENERATED",
                resource_type="PATIENT",
                resource_id=patient_id,
                details={
                    "query_type": query_type.value,
                    "safety_status": validated_response.safety_status.value,
                    "evidence_count": len(relevant_evidence),
                    "latency_ms": latency_ms,
                },
            )
        )
        await db.commit()
        return validated_response

    async def get_message(
        self, db: AsyncSession, message_id: str
    ) -> CopilotMessageResponse:
        stmt = select(CopilotMessage).where(CopilotMessage.id == message_id)
        res = await db.execute(stmt)
        msg = res.scalar_one_or_none()
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Copilot message not found.",
            )
        return CopilotMessageResponse.model_validate(msg)

    async def get_message_evidence(
        self, db: AsyncSession, message_id: str
    ) -> List[Dict[str, Any]]:
        stmt = select(CopilotMessage).where(CopilotMessage.id == message_id)
        res = await db.execute(stmt)
        msg = res.scalar_one_or_none()
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Copilot message not found.",
            )
        
        # Extract evidence items from structured response
        struct = msg.structured_response or {}
        items = struct.get("evidence_items", [])
        return items

    async def submit_feedback(
        self,
        db: AsyncSession,
        message_id: str,
        clinician_id: str,
        payload: CopilotFeedbackCreate,
    ) -> CopilotFeedbackResponse:
        stmt = select(CopilotMessage).where(CopilotMessage.id == message_id)
        res = await db.execute(stmt)
        msg = res.scalar_one_or_none()
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Copilot message not found.",
            )

        feedback = CopilotFeedback(
            message_id=message_id,
            clinician_id=clinician_id,
            patient_id=msg.patient_id,
            rating=payload.rating,
            feedback_category=payload.feedback_category.value,
            comments=payload.comments,
        )
        db.add(feedback)
        await db.flush()

        db.add(
            AuditLog(
                actor_id=clinician_id,
                action="COPILOT_FEEDBACK_SUBMITTED",
                resource_type="COPILOT_MESSAGE",
                resource_id=message_id,
                details={"rating": payload.rating, "category": payload.feedback_category.value},
            )
        )
        await db.commit()
        await db.refresh(feedback)
        return CopilotFeedbackResponse.model_validate(feedback)
