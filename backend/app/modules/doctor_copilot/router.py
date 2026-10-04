from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_token
from app.modules.doctor_copilot.schemas import (
    CopilotFeedbackCreate,
    CopilotFeedbackResponse,
    CopilotMessageResponse,
    CopilotQueryRequest,
    CopilotSessionCreate,
    CopilotSessionResponse,
    StructuredCopilotResponse,
)
from app.modules.doctor_copilot.service import DoctorCopilotService

router = APIRouter()
copilot_service = DoctorCopilotService()


@router.post(
    "/patients/{patient_id}/copilot/sessions",
    response_model=CopilotSessionResponse,
    summary="Create a new Doctor Copilot clinical session for a patient",
)
async def create_copilot_session(
    patient_id: str,
    payload: CopilotSessionCreate,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    clinician_id = current_user.get("sub")
    session = await copilot_service.create_session(
        db=db,
        patient_id=patient_id,
        clinician_id=clinician_id,
        payload=payload,
    )
    return CopilotSessionResponse(
        id=session.id,
        patient_id=session.patient_id,
        clinician_id=session.clinician_id,
        title=session.title,
        status=session.status,

        context_version=session.context_version,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get(
    "/patients/{patient_id}/copilot/sessions",
    response_model=List[CopilotSessionResponse],
    summary="List all Doctor Copilot sessions for a patient",
)
async def list_copilot_sessions(
    patient_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    return await copilot_service.list_sessions(
        db=db, patient_id=patient_id, limit=limit, offset=offset
    )


@router.get(
    "/copilot/sessions/{session_id}",
    summary="Get details and message history for a Copilot session",
)
async def get_copilot_session(
    session_id: str,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    session = await copilot_service.get_session(db=db, session_id=session_id)
    return {
        "id": session.id,
        "patient_id": session.patient_id,
        "clinician_id": session.clinician_id,
        "title": session.title,
        "status": session.status,
        "context_version": session.context_version,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "query_type": m.query_type,
                "structured_response": m.structured_response,
                "evidence_ids": m.evidence_ids,
                "safety_status": m.safety_status,
                "created_at": m.created_at,
            }
            for m in session.messages
        ],
    }


@router.post(
    "/copilot/sessions/{session_id}/messages",
    response_model=StructuredCopilotResponse,
    summary="Post a question inside an existing Copilot session",
)
async def send_session_message(
    session_id: str,
    payload: CopilotQueryRequest,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    clinician_id = current_user.get("sub")
    session = await copilot_service.get_session(db=db, session_id=session_id)
    payload.session_id = session.id
    return await copilot_service.query_copilot(
        db=db,
        patient_id=session.patient_id,
        clinician_id=clinician_id,
        payload=payload,
    )


@router.post(
    "/patients/{patient_id}/copilot/query",
    response_model=StructuredCopilotResponse,
    summary="Directly query Doctor Copilot on a patient's verified record",
)
async def direct_copilot_query(
    patient_id: str,
    payload: CopilotQueryRequest,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    clinician_id = current_user.get("sub")
    return await copilot_service.query_copilot(
        db=db,
        patient_id=patient_id,
        clinician_id=clinician_id,
        payload=payload,
    )


@router.get(
    "/copilot/messages/{message_id}",
    response_model=CopilotMessageResponse,
    summary="Get a specific Copilot message",
)
async def get_copilot_message(
    message_id: str,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    return await copilot_service.get_message(db=db, message_id=message_id)


@router.get(
    "/copilot/messages/{message_id}/evidence",
    summary="Get detailed clinical evidence items cited in a Copilot message",
)
async def get_message_evidence(
    message_id: str,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    return await copilot_service.get_message_evidence(db=db, message_id=message_id)


@router.post(
    "/copilot/messages/{message_id}/feedback",
    response_model=CopilotFeedbackResponse,
    summary="Submit clinician feedback on a Copilot answer",
)
async def submit_copilot_feedback(
    message_id: str,
    payload: CopilotFeedbackCreate,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    clinician_id = current_user.get("sub")
    return await copilot_service.submit_feedback(
        db=db,
        message_id=message_id,
        clinician_id=clinician_id,
        payload=payload,
    )

