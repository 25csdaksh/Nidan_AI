import json
import re
from typing import Any, Dict, List
from app.modules.doctor_copilot.schemas import (
    ClaimItem,
    EvidenceItem,
    QueryType,
    SafetyStatus,
    StructuredCopilotResponse,
    SupportLevel,
)


def parse_copilot_llm_response(
    raw_response: str,
    query_type: QueryType,
    evidence_items: List[EvidenceItem],
    prompt_version: str = "1.0",
    context_version: str = "1.0",
    model_provider: str = "nidan-deterministic",
    model_version: str = "1.0",
) -> StructuredCopilotResponse:
    """
    Safely parses JSON LLM response with robust fallback.
    """
    try:
        # Strip potential markdown code blocks ```json ... ```
        clean_text = raw_response.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n?", "", clean_text)
            clean_text = re.sub(r"\n?```$", "", clean_text).strip()

        data = json.loads(clean_text)

        claims_raw = data.get("claims", [])
        parsed_claims: List[ClaimItem] = []
        for c in claims_raw:
            if isinstance(c, dict) and "claim" in c:
                parsed_claims.append(
                    ClaimItem(
                        claim=c.get("claim", ""),
                        evidence_ids=c.get("evidence_ids", []),
                        support_level=SupportLevel(c.get("support_level", "SUPPORTED"))
                        if c.get("support_level") in [s.value for s in SupportLevel]
                        else SupportLevel.SUPPORTED,
                    )
                )

        return StructuredCopilotResponse(
            answer=data.get("answer", "No structured answer generated."),
            claims=parsed_claims,
            limitations=data.get("limitations", []),
            data_quality_notes=data.get("data_quality_notes", []),
            requires_clinician_review=True,
            safety_status=SafetyStatus.PASSED,
            query_type=query_type,
            evidence_items=evidence_items,
            prompt_version=prompt_version,
            context_version=context_version,
            safety_version="1.0",
            model_provider=model_provider,
            model_version=model_version,
        )
    except Exception:
        # Robust fallback if raw response was unstructured text
        # Extract default evidence IDs
        default_evidence_ids = [e.evidence_id for e in evidence_items[:5]]
        default_claim = ClaimItem(
            claim=raw_response[:200] if len(raw_response) > 200 else raw_response,
            evidence_ids=default_evidence_ids,
            support_level=SupportLevel.SUPPORTED if default_evidence_ids else SupportLevel.PARTIALLY_SUPPORTED,
        )
        return StructuredCopilotResponse(
            answer=raw_response,
            claims=[default_claim] if raw_response else [],
            limitations=["Response synthesized in fallback non-JSON format."],
            data_quality_notes=[],
            requires_clinician_review=True,
            safety_status=SafetyStatus.PASSED,
            query_type=query_type,
            evidence_items=evidence_items,
            prompt_version=prompt_version,
            context_version=context_version,
            safety_version="1.0",
            model_provider=model_provider,
            model_version=model_version,
        )
