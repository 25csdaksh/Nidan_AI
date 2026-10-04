import abc
import json
import logging
from typing import Any, Dict, List, Optional
from app.modules.doctor_copilot.schemas import (
    ClaimItem,
    EvidenceItem,
    EvidenceType,
    QueryType,
    SafetyStatus,
    StructuredCopilotResponse,
    SupportLevel,
)
from app.modules.doctor_copilot.llm.response_parser import parse_copilot_llm_response

logger = logging.getLogger("nidan_ai.doctor_copilot.provider")


class BaseCopilotLLMProvider(abc.ABC):
    """
    Abstract interface for Copilot language generation backends.
    """

    @abc.abstractmethod
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        query_type: QueryType,
        evidence_items: List[EvidenceItem],
        patient_context: Dict[str, Any],
    ) -> StructuredCopilotResponse:
        pass


class DeterministicCopilotEngine(BaseCopilotLLMProvider):
    """
    Deterministic clinical synthesis engine for NIDAN AI.
    Generates rich, evidence-grounded, non-hallucinatory structured responses
    directly from verified patient observations, trends, and medication records.
    """

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        query_type: QueryType,
        evidence_items: List[EvidenceItem],
        patient_context: Dict[str, Any],
    ) -> StructuredCopilotResponse:
        claims: List[ClaimItem] = []
        limitations: List[str] = list(patient_context.get("data_quality_notes", []))
        answer_parts: List[str] = []

        patient_info = patient_context.get("patient", {})
        first_name = patient_info.get("first_name", "Patient")
        last_name = patient_info.get("last_name", "")
        pt_name = f"{first_name} {last_name}".strip()

        # 1. GENERAL MEDICAL KNOWLEDGE
        if query_type == QueryType.GENERAL_MEDICAL_KNOWLEDGE:
            answer_parts.append(
                "General Clinical Information: Laboratory analytes reflect physiological organ function and metabolic equilibrium. "
                "For example, HbA1c measures average glycated hemoglobin over 2-3 months, while Serum Creatinine and eGFR assess renal clearance."
            )
            # Add patient context if available
            lab_items = [e for e in evidence_items if e.type == EvidenceType.LAB_RESULT]
            if lab_items:
                obs_summary = ", ".join([f"{e.title} ({e.value} {e.unit or ''} on {e.date or 'unknown date'})" for e in lab_items[:3]])
                answer_parts.append(f"Patient-Specific Context: In {pt_name}'s record, the following relevant observations are documented: {obs_summary}.")
                for e in lab_items[:3]:
                    claims.append(ClaimItem(claim=f"{e.title}: {e.value} {e.unit or ''} documented on {e.date or 'unknown date'}.", evidence_ids=[e.evidence_id]))
            else:
                answer_parts.append(f"Patient-Specific Context: No specific laboratory values matching this analyte are documented in {pt_name}'s current record.")

        # 2. PATIENT CONSULTATION SUMMARY
        elif query_type == QueryType.PATIENT_SUMMARY:
            answer_parts.append(f"Clinical Summary for {pt_name} (MRN: {patient_info.get('mrn', 'UNKNOWN')}):")
            
            # Lab findings
            finding_items = [e for e in evidence_items if e.type == EvidenceType.CLINICAL_FINDING]
            if finding_items:
                find_text = "; ".join([f"{f.title} ({f.value or ''} {f.unit or ''}, {f.severity or 'STATUS_NOTED'})" for f in finding_items[:4]])
                answer_parts.append(f"Key Clinical Findings: {find_text}.")
                for f in finding_items[:4]:
                    claims.append(ClaimItem(claim=f"Clinical Finding: {f.title} ({f.value or ''} {f.unit or ''}).", evidence_ids=[f.evidence_id]))
            
            # Trends
            trend_items = [e for e in evidence_items if e.type == EvidenceType.LONGITUDINAL_TREND]
            if trend_items:
                trend_text = "; ".join([f"{t.title} ({t.value})" for t in trend_items[:3]])
                answer_parts.append(f"Longitudinal Trajectories: {trend_text}.")
                for t in trend_items[:3]:
                    claims.append(ClaimItem(claim=f"Trajectory: {t.title} with {t.value}.", evidence_ids=[t.evidence_id]))

            # Medications
            med_items = [e for e in evidence_items if e.type == EvidenceType.MEDICATION]
            if med_items:
                med_text = ", ".join([f"{m.title} ({m.value or 'strength unstated'})" for m in med_items[:4]])
                answer_parts.append(f"Documented Medications: {med_text}.")
                for m in med_items[:4]:
                    claims.append(ClaimItem(claim=f"Prescription record: {m.title}.", evidence_ids=[m.evidence_id]))

            # Safety signals
            safety_items = [e for e in evidence_items if e.type == EvidenceType.MEDICATION_SAFETY]
            if safety_items:
                saf_text = "; ".join([f"{s.title} ({s.severity or 'INFO'})" for s in safety_items[:3]])
                answer_parts.append(f"Medication Safety Signals Requiring Review: {saf_text}.")
                for s in safety_items[:3]:
                    claims.append(ClaimItem(claim=f"Safety observation: {s.title}.", evidence_ids=[s.evidence_id]))

        # 3. LAB COMPARISON
        elif query_type == QueryType.LAB_COMPARISON:
            answer_parts.append(f"Laboratory Encounter Comparison for {pt_name}:")
            trend_items = [e for e in evidence_items if e.type == EvidenceType.LONGITUDINAL_TREND]
            lab_items = [e for e in evidence_items if e.type == EvidenceType.LAB_RESULT]

            if trend_items:
                for t in trend_items[:5]:
                    answer_parts.append(f"- {t.title}: {t.value} (Dynamics: {t.severity or 'EVALUATED'}).")
                    claims.append(ClaimItem(claim=f"{t.title}: {t.value}.", evidence_ids=[t.evidence_id]))
            elif lab_items:
                for l in lab_items[:6]:
                    answer_parts.append(f"- {l.title}: {l.value} {l.unit or ''} on {l.date or 'UNKNOWN'} (Status: {l.status or 'NOTED'}).")
                    claims.append(ClaimItem(claim=f"{l.title}: {l.value} {l.unit or ''} on {l.date or 'UNKNOWN'}.", evidence_ids=[l.evidence_id]))
            else:
                answer_parts.append("Insufficient multi-encounter laboratory observations to contrast values.")

        # 4. TRENDS & TRAJECTORIES
        elif query_type == QueryType.TREND_QUERY:
            answer_parts.append(f"Longitudinal Trajectory Analysis for {pt_name}:")
            trend_items = [e for e in evidence_items if e.type == EvidenceType.LONGITUDINAL_TREND]
            if trend_items:
                for t in trend_items:
                    answer_parts.append(f"- {t.title}: {t.value} (Status: {t.status or 'RECORDED'}).")
                    claims.append(ClaimItem(claim=f"Trend for {t.title}: {t.value}.", evidence_ids=[t.evidence_id]))
            else:
                answer_parts.append("No multi-visit longitudinal trends currently computed for this patient.")

        # 5. ABNORMALITIES
        elif query_type == QueryType.ABNORMALITY_QUERY:
            answer_parts.append(f"Identified Laboratory Abnormalities & Findings for {pt_name}:")
            abn_items = [e for e in evidence_items if e.type == EvidenceType.CLINICAL_FINDING or e.status in ["ABNORMAL", "HIGH", "LOW", "CRITICAL_HIGH", "CRITICAL_LOW"]]
            if abn_items:
                for ab in abn_items:
                    ref_text = f" [Ref: {ab.reference_range}]" if ab.reference_range else ""
                    answer_parts.append(f"- {ab.title}: {ab.value or ''} {ab.unit or ''}{ref_text} (Severity/Status: {ab.severity or ab.status or 'NOTED'}).")
                    claims.append(ClaimItem(claim=f"{ab.title} recorded as {ab.value or ''} {ab.unit or ''}.", evidence_ids=[ab.evidence_id]))
            else:
                answer_parts.append("No abnormal laboratory findings or critical flags were identified in the available records.")

        # 6. MEDICATION SAFETY & INTERACTIONS
        elif query_type == QueryType.MEDICATION_SAFETY_QUERY:
            answer_parts.append(f"Medication Safety Review for {pt_name}:")
            safety_items = [e for e in evidence_items if e.type == EvidenceType.MEDICATION_SAFETY]
            if safety_items:
                for s in safety_items:
                    answer_parts.append(f"- [{s.severity or 'REVIEW'}] {s.title} (Status: {s.status or 'IDENTIFIED'}).")
                    claims.append(ClaimItem(claim=f"Safety Finding: {s.title}.", evidence_ids=[s.evidence_id]))
            else:
                answer_parts.append("No medication safety alerts or drug interactions were triggered by the current rule set.")

        # 7. MEDICATIONS & PRESCRIPTIONS
        elif query_type in [QueryType.MEDICATION_QUERY, QueryType.PRESCRIPTION_QUERY]:
            answer_parts.append(f"Documented Medications & Prescriptions for {pt_name}:")
            med_items = [e for e in evidence_items if e.type in [EvidenceType.MEDICATION, EvidenceType.PRESCRIPTION]]
            if med_items:
                for m in med_items:
                    detail_str = f" - {m.value}" if m.value else ""
                    answer_parts.append(f"- {m.title}{detail_str} (Review Status: {m.review_status or 'DOCUMENTED'}).")
                    claims.append(ClaimItem(claim=f"{m.title}{detail_str}.", evidence_ids=[m.evidence_id]))
            else:
                answer_parts.append("No active or historical prescription medications are documented in the available record.")

        # 8. DATA QUALITY
        elif query_type == QueryType.DATA_QUALITY_QUERY:
            answer_parts.append(f"Data Quality & Record Completeness Assessment for {pt_name}:")
            dq_notes = patient_context.get("data_quality_notes", [])
            if dq_notes:
                for note in dq_notes:
                    answer_parts.append(f"- Note: {note}")
                    claims.append(ClaimItem(claim=note, evidence_ids=[evidence_items[0].evidence_id] if evidence_items else []))
            else:
                answer_parts.append("Patient record has verified laboratory observations, prescriptions, and demographic metadata.")

        # 9. GENERAL / OTHER QUERY
        else:
            answer_parts.append(f"Clinical Observations for {pt_name}:")
            for e in evidence_items[:5]:
                val_text = f": {e.value} {e.unit or ''}" if e.value else ""
                answer_parts.append(f"- {e.title}{val_text} ({e.date or 'Date unstated'}).")
                claims.append(ClaimItem(claim=f"{e.title}{val_text}.", evidence_ids=[e.evidence_id]))

        full_answer = "\n".join(answer_parts)
        if not full_answer.strip():
            full_answer = "No matching clinical evidence found in the available patient records."

        return StructuredCopilotResponse(
            answer=full_answer,
            claims=claims,
            limitations=limitations,
            data_quality_notes=patient_context.get("data_quality_notes", []),
            requires_clinician_review=True,
            safety_status=SafetyStatus.PASSED,
            query_type=query_type,
            evidence_items=evidence_items,
            prompt_version="1.0",
            context_version="1.0",
            safety_version="1.0",
            model_provider="nidan-deterministic",
            model_version="1.0",
        )


class MockCopilotLLMProvider(BaseCopilotLLMProvider):
    """
    Mock LLM provider for testing specific response scenarios (e.g. malformed output, timeouts).
    """

    def __init__(self, override_response: Optional[str] = None):
        self.override_response = override_response
        self.deterministic_engine = DeterministicCopilotEngine()

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        query_type: QueryType,
        evidence_items: List[EvidenceItem],
        patient_context: Dict[str, Any],
    ) -> StructuredCopilotResponse:
        if self.override_response:
            return parse_copilot_llm_response(
                self.override_response,
                query_type=query_type,
                evidence_items=evidence_items,
            )
        return await self.deterministic_engine.generate_response(
            system_prompt, user_prompt, query_type, evidence_items, patient_context
        )
