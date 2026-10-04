import re
from typing import Optional, Tuple
from app.modules.doctor_copilot.schemas import QueryType, StructuredCopilotResponse, SafetyStatus, SupportLevel

PROHIBITED_PATTERNS = [
    (r"\b(prescribe|give rx for|write prescription for|order medication)\b", "Autonomous prescription generation is prohibited."),
    (r"\b(recommend (changing|increasing|decreasing|adjusting)?\s*(the\s*)?(medication|drug|dose|dosage|antibiotic|insulin|treatment plan))\b", "Autonomous medication or dosage recommendation is prohibited."),
    (r"\b(diagnose|confirm diagnosis of|does the patient have (cancer|diabetes|ckd|anemia|infection))\b", "Autonomous disease diagnosis is prohibited."),
    (r"\b(start|stop|titrate|increase (the )?dose|decrease (the )?dose|change (the )?dose|adjust (the )?dose)\b", "Medication initiation, discontinuation, and titration recommendations are prohibited."),
    (r"\b(predict prognosis|life expectancy|survival rate|will the patient die)\b", "Prognostic and survival rate predictions are prohibited."),
]



def is_prohibited_request(query: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if a query requests an autonomous clinical or prescribing action.
    Returns (is_prohibited, reason).
    """
    q = query.lower().strip()
    # If the user is asking to summarize/show safety findings or interactions, it's allowed
    if any(k in q for k in ["safety finding", "interaction", "summarize", "show evidence", "what is documented"]):
        return False, None

    for pattern, reason in PROHIBITED_PATTERNS:
        if re.search(pattern, q):
            return True, reason

    return False, None


def build_prohibited_refusal(query: str, reason: str) -> StructuredCopilotResponse:
    """
    Generates a safe, professional refusal explaining CDSS boundaries.
    """
    refusal_text = (
        f"NIDAN AI cannot perform this request because {reason.lower()} "
        "As an assistive Clinical Decision Support System (CDSS), NIDAN AI surfaces verified laboratory "
        "trajectories, extracted medication records, and safety observations for human clinician review, "
        "but does not independently diagnose conditions, prescribe medications, or recommend therapeutic changes. "
        "Please review the verified clinical findings and consult appropriate clinical protocols."
    )
    return StructuredCopilotResponse(
        answer=refusal_text,
        claims=[],
        limitations=["Autonomous clinical decision-making is restricted by CDSS safety guardrails."],
        data_quality_notes=[],
        requires_clinician_review=True,
        safety_status=SafetyStatus.PROHIBITED_REQUEST,
        query_type=QueryType.PROHIBITED_CLINICAL_DECISION,
        evidence_items=[],
        prompt_version="1.0",
        context_version="1.0",
        safety_version="1.0",
        model_provider="nidan-deterministic",
        model_version="1.0",
    )
