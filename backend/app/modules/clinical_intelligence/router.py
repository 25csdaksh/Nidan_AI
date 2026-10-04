from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    get_current_user_token,
    require_roles,
    UserRole,
    CLINICAL_STAFF_ROLES,
)
from app.modules.clinical_intelligence.models import (
    FindingReviewStatusEnum,
)
from app.modules.clinical_intelligence.schemas import (
    ClinicalAnalysisResponse,
    ClinicalFindingResponse,
    ClinicalRuleMetadataResponse,
    FindingReviewRequest,
    PatientLongitudinalResponse,
    PatientTimelineResponse,
    LongitudinalAnalysisRequest,
    LongitudinalAnalysisResponse,
    LongitudinalReviewNoteCreate,
    LongitudinalReviewNoteResponse,
    VisitComparisonRequest,
    CrossVisitComparisonResponse,
)
from app.modules.clinical_intelligence.service import ClinicalIntelligenceService
from app.modules.clinical_intelligence.reference_ranges.repository import ReferenceRangeRepository
from app.modules.clinical_intelligence.reference_ranges.schemas import ReferenceRangeResponse

router = APIRouter()


def _enforce_patient_access(token: dict, patient_id: str):
    """Enforces that a patient role user can only view their own records."""
    user_role = token.get("role")
    if user_role == UserRole.PATIENT.value:
        token_patient_id = token.get("patient_id")
        if token_patient_id and token_patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients may only access their own clinical records.",
            )


# ---------------------------------------------------------------------
# Phase 3: Single-Document Clinical Analysis & Findings
# ---------------------------------------------------------------------

@router.post(
    "/medical-documents/{document_id}/clinical-analysis",
    response_model=ClinicalAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Deterministic Clinical Intelligence Analysis",
)
async def trigger_clinical_analysis(
    document_id: str,
    request: Request,
    force_reanalyze: bool = Query(False, description="Force re-evaluation of clinical findings"),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """
    Executes the deterministic, versioned Clinical Anomaly Detection and Blood Report
    Intelligence Engine on verified extracted lab entities.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    actor_id = token.get("sub")

    service = ClinicalIntelligenceService(db)
    try:
        analysis = await service.run_clinical_analysis(
            document_id=document_id,
            force_reanalyze=force_reanalyze,
            actor_id=actor_id,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return ClinicalAnalysisResponse.model_validate(analysis)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Clinical analysis error: {str(e)}")


@router.get(
    "/medical-documents/{document_id}/clinical-analysis",
    response_model=Optional[ClinicalAnalysisResponse],
    summary="Get Structured Clinical Analysis Results",
)
async def get_document_clinical_analysis(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """Fetches the latest completed clinical analysis and structured findings for a document."""
    service = ClinicalIntelligenceService(db)
    analysis = await service.get_document_analysis(document_id)
    if not analysis:
        return None
    return ClinicalAnalysisResponse.model_validate(analysis)


@router.get(
    "/medical-documents/{document_id}/clinical-findings",
    response_model=List[ClinicalFindingResponse],
    summary="List Clinical Findings for Document",
)
async def list_document_clinical_findings(
    document_id: str,
    finding_type: Optional[str] = Query(None, description="Filter by finding type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by finding status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    service = ClinicalIntelligenceService(db)
    findings = await service.list_findings(
        document_id=document_id,
        finding_type=finding_type,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return [ClinicalFindingResponse.model_validate(f) for f in findings]


@router.get(
    "/patients/{patient_id}/clinical-findings",
    response_model=PatientLongitudinalResponse,
    summary="Get Patient Longitudinal Findings Timeline",
)
async def get_patient_longitudinal_findings(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    _enforce_patient_access(token, patient_id)
    service = ClinicalIntelligenceService(db)
    return await service.get_patient_longitudinal_series(patient_id)


@router.get(
    "/clinical-rules",
    response_model=List[ClinicalRuleMetadataResponse],
    summary="Get Active Clinical Rule Metadata",
)
async def get_clinical_rules(
    token: dict = Depends(require_roles(CLINICAL_STAFF_ROLES)),
):
    """Provides auditable metadata of all active deterministic clinical rules."""
    service = ClinicalIntelligenceService(None)
    metadata = service.get_active_rules_metadata()
    return [ClinicalRuleMetadataResponse.model_validate(m) for m in metadata]


@router.post(
    "/clinical-findings/{finding_id}/review",
    response_model=ClinicalFindingResponse,
    summary="Doctor Review & Adjudication of Clinical Finding",
)
async def review_clinical_finding(
    finding_id: str,
    payload: FindingReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(require_roles(CLINICAL_STAFF_ROLES)),
):
    """
    Allows licensed clinicians to ACCEPT, MODIFY, or REJECT automated findings
    with full immutable audit trail recording.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    reviewer_id = token.get("sub", "00000000-0000-0000-0000-000000000001")

    service = ClinicalIntelligenceService(db)
    try:
        updated_finding = await service.review_finding(
            finding_id=finding_id,
            review_data=payload,
            reviewer_id=reviewer_id,
            actor_id=reviewer_id,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return ClinicalFindingResponse.model_validate(updated_finding)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/clinical-intelligence/reference-ranges",
    response_model=List[ReferenceRangeResponse],
    summary="Query Reference Range Knowledge Base",
)
async def list_reference_ranges(
    panel: Optional[str] = Query(None, description="Filter by lab panel"),
    canonical_name: Optional[str] = Query(None, description="Filter by analyte canonical name"),
    sex: Optional[str] = Query(None, description="Filter by sex (male, female, all)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    repo = ReferenceRangeRepository(db)
    items = await repo.list_ranges(
        panel=panel,
        canonical_name=canonical_name,
        sex=sex,
        skip=skip,
        limit=limit,
    )
    return [ReferenceRangeResponse.model_validate(i) for i in items]


# ---------------------------------------------------------------------
# Phase 4: Longitudinal Intelligence Endpoints
# ---------------------------------------------------------------------

@router.get(
    "/patients/{patient_id}/timeline",
    response_model=PatientTimelineResponse,
    summary="Get Patient Observation Timeline",
)
async def get_patient_timeline(
    patient_id: str,
    start_date: Optional[str] = Query(None, description="Filter start date ISO"),
    end_date: Optional[str] = Query(None, description="Filter end date ISO"),
    analyte: Optional[str] = Query(None, description="Filter by analyte name"),
    panel: Optional[str] = Query(None, description="Filter by panel"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (LOW, HIGH, NORMAL)"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """
    Returns the normalized longitudinal timeline of clinical observations grouped
    chronologically by visit/document for the given patient.
    """
    _enforce_patient_access(token, patient_id)
    service = ClinicalIntelligenceService(db)
    return await service.get_patient_timeline(
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
        analyte=analyte,
        panel=panel,
        status=status_filter,
        document_type=document_type,
    )


@router.get(
    "/patients/{patient_id}/trends",
    summary="Get All Patient Analyte Trends",
)
async def get_patient_trends(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """
    Evaluates multi-observation trends across all analytes for a patient.
    """
    _enforce_patient_access(token, patient_id)
    service = ClinicalIntelligenceService(db)
    return await service.get_patient_trends(patient_id=patient_id)


@router.get(
    "/patients/{patient_id}/trends/{analyte}",
    summary="Get Specific Analyte Trend",
)
async def get_patient_analyte_trend(
    patient_id: str,
    analyte: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """
    Evaluates trend direction, percentage delta, and clinical status for a specific analyte.
    """
    _enforce_patient_access(token, patient_id)
    service = ClinicalIntelligenceService(db)
    trends = await service.get_patient_trends(patient_id=patient_id, analyte=analyte)
    if not trends:
        return {"analyte": analyte, "trend_status": "INSUFFICIENT_DATA", "observation_count": 0}
    return trends[0]


@router.post(
    "/patients/{patient_id}/longitudinal-analysis",
    response_model=LongitudinalAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Longitudinal Clinical Intelligence Analysis",
)
async def trigger_longitudinal_analysis(
    patient_id: str,
    payload: Optional[LongitudinalAnalysisRequest] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """
    Executes the multi-visit cross-document longitudinal analysis engine,
    evaluating persistent abnormalities, new/resolved findings, fluctuations,
    panel completeness, and auditable summary sections.
    """
    _enforce_patient_access(token, patient_id)
    client_ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    actor_id = token.get("sub")

    service = ClinicalIntelligenceService(db)
    analysis = await service.run_longitudinal_analysis(
        patient_id=patient_id,
        request_data=payload,
        actor_id=actor_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    return LongitudinalAnalysisResponse.model_validate(analysis)


@router.get(
    "/patients/{patient_id}/longitudinal-analysis",
    response_model=Optional[LongitudinalAnalysisResponse],
    summary="Get Latest Longitudinal Analysis",
)
async def get_latest_longitudinal_analysis(
    patient_id: str,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    _enforce_patient_access(token, patient_id)
    client_ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    actor_id = token.get("sub")

    service = ClinicalIntelligenceService(db)
    analysis = await service.get_patient_longitudinal_analysis(
        patient_id=patient_id,
        actor_id=actor_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    if not analysis:
        return None
    return LongitudinalAnalysisResponse.model_validate(analysis)


@router.get(
    "/patients/{patient_id}/longitudinal-analysis/{analysis_id}",
    response_model=Optional[LongitudinalAnalysisResponse],
    summary="Get Specific Versioned Longitudinal Analysis",
)
async def get_specific_longitudinal_analysis(
    patient_id: str,
    analysis_id: str,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    _enforce_patient_access(token, patient_id)
    client_ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    actor_id = token.get("sub")

    service = ClinicalIntelligenceService(db)
    analysis = await service.get_patient_longitudinal_analysis(
        patient_id=patient_id,
        analysis_id=analysis_id,
        actor_id=actor_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Longitudinal analysis not found.")
    return LongitudinalAnalysisResponse.model_validate(analysis)


@router.post(
    "/patients/{patient_id}/compare-visits",
    response_model=CrossVisitComparisonResponse,
    summary="Compare Two Patient Visits",
)
async def compare_patient_visits(
    patient_id: str,
    payload: VisitComparisonRequest,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    """
    Direct analyte-by-analyte comparison between two clinical reports/visits.
    """
    _enforce_patient_access(token, patient_id)
    client_ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    actor_id = token.get("sub")

    service = ClinicalIntelligenceService(db)
    result = await service.compare_patient_visits(
        patient_id=patient_id,
        visit_a_doc_id=payload.visit_a_document_id,
        visit_b_doc_id=payload.visit_b_document_id,
        actor_id=actor_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    return CrossVisitComparisonResponse.model_validate(result.model_dump())


@router.post(
    "/patients/{patient_id}/longitudinal-review-notes",
    response_model=LongitudinalReviewNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Clinician Longitudinal Review Note",
)
async def create_longitudinal_review_note(
    patient_id: str,
    payload: LongitudinalReviewNoteCreate,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(require_roles(CLINICAL_STAFF_ROLES)),
):
    """
    Allows authorized clinicians to append clinical notes and annotations to
    a patient's longitudinal record. Patients cannot create clinician notes.
    """
    client_ip = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    author_id = token.get("sub", "00000000-0000-0000-0000-000000000001")

    service = ClinicalIntelligenceService(db)
    note = await service.create_review_note(
        patient_id=patient_id,
        note_data=payload,
        author_id=author_id,
        actor_id=author_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    return LongitudinalReviewNoteResponse.model_validate(note)


@router.get(
    "/patients/{patient_id}/longitudinal-review-notes",
    response_model=List[LongitudinalReviewNoteResponse],
    summary="List Clinician Longitudinal Review Notes",
)
async def list_longitudinal_review_notes(
    patient_id: str,
    analysis_id: Optional[str] = Query(None, description="Filter by analysis ID"),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    _enforce_patient_access(token, patient_id)
    service = ClinicalIntelligenceService(db)
    notes = await service.list_review_notes(patient_id=patient_id, analysis_id=analysis_id)
    return [LongitudinalReviewNoteResponse.model_validate(n) for n in notes]
