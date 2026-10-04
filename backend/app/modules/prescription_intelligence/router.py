"""FastAPI Router for Prescription Intelligence & Medication Safety (Phase 5).

Exposes:
- Document-level prescription extraction trigger and status
- Prescription headers and normalized medication lists
- Patient longitudinal medication timelines
- Multi-engine medication safety analysis (DDIs, allergies, duplicates, lab context, contraindications)
- Safety finding details and clinician review endpoints
- Safety knowledge base rules catalog
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_token
from app.modules.prescription_intelligence.models import Prescription
from app.modules.prescription_intelligence.schemas import (
    MedicationReviewRequest,
    MedicationReviewResponse,
    MedicationRuleResponse,
    MedicationSafetyAnalysisRequest,
    MedicationSafetyAnalysisResponse,
    MedicationSafetyFindingResponse,
    PatientMedicationTimelineResponse,
    PrescriptionMedicationResponse,
    PrescriptionResponse,
)
from app.modules.prescription_intelligence.service import PrescriptionIntelligenceService

prescription_intelligence_router = APIRouter()


# 1. Document Extraction Endpoints
@prescription_intelligence_router.post(
    "/medical-documents/{document_id}/prescription-extraction",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Prescription Extraction on Medical Document",
)
async def trigger_prescription_extraction(
    document_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_token),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    svc = PrescriptionIntelligenceService(db)
    return await svc.extract_prescription_from_document(
        document_id=document_id,
        current_user=current_user,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@prescription_intelligence_router.get(
    "/medical-documents/{document_id}/prescription",
    response_model=Optional[PrescriptionResponse],
    summary="Get Extracted Prescription for Medical Document",
)
async def get_document_prescription(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_token),
):
    svc = PrescriptionIntelligenceService(db)
    return await svc.get_prescription_by_document(document_id, current_user)


# 2. Prescription Records Endpoints
@prescription_intelligence_router.get(
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionResponse,
    summary="Get Prescription by ID",
)
async def get_prescription(
    prescription_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_token),
):
    svc = PrescriptionIntelligenceService(db)
    return await svc.get_prescription(prescription_id, current_user)


@prescription_intelligence_router.get(
    "/patients/{patient_id}/prescriptions",
    response_model=List[PrescriptionResponse],
    summary="List Prescriptions for Patient",
)
async def list_patient_prescriptions(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_token),
):
    svc = PrescriptionIntelligenceService(db)
    prescriptions, _ = await svc.get_patient_prescriptions(
        patient_id=patient_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
        status=status,
    )
    return prescriptions


# 3. Patient Medications & Longitudinal Timeline
@prescription_intelligence_router.get(
    "/patients/{patient_id}/medications",
    response_model=List[PrescriptionMedicationResponse],
    summary="List All Extracted Medications for Patient",
)
async def list_patient_medications(
    patient_id: str,
    canonical_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_token),
):
    svc = PrescriptionIntelligenceService(db)
    return await svc.get_patient_medications(
        patient_id=patient_id,
        current_user=current_user,
        canonical_name=canonical_name,
    )


@prescription_intelligence_router.get(
    "/patients/{patient_id}/medication-timeline",
    response_model=PatientMedicationTimelineResponse,
    summary="Get Patient Longitudinal Medication Timeline",
)
async def get_patient_medication_timeline(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_token),
):
    svc = PrescriptionIntelligenceService(db)
    return await svc.get_patient_medication_timeline(patient_id, current_user)


# 4. Medication Safety Analysis Endpoints
@prescription_intelligence_router.post(
    "/patients/{patient_id}/medication-safety-analysis",
    response_model=MedicationSafetyAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Multi-Engine Medication Safety Analysis",
)
async def run_medication_safety_analysis(
    patient_id: str,
    request: Request,
    request_data: MedicationSafetyAnalysisRequest = MedicationSafetyAnalysisRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_token),
):
    client_ip = request.client.host if request.client else None
    svc = PrescriptionIntelligenceService(db)
    findings = await svc.run_medication_safety_analysis(
        patient_id=patient_id,
        request_data=request_data,
        current_user=current_user,
        client_ip=client_ip,
    )
    meds = await svc.get_patient_medications(patient_id, current_user)
    prescs, _ = await svc.get_patient_prescriptions(patient_id, current_user)

    crit_cnt = sum(1 for f in findings if f.severity == "CRITICAL")
    high_cnt = sum(1 for f in findings if f.severity == "HIGH")
    mod_cnt = sum(1 for f in findings if f.severity == "MODERATE")
    info_cnt = sum(1 for f in findings if f.severity in ["INFO", "LOW"])
    pending_cnt = sum(1 for f in findings if f.review_status == "PENDING")

    return MedicationSafetyAnalysisResponse(
        patient_id=patient_id,
        prescriptions_analyzed=len(prescs),
        medications_analyzed=len(meds),
        findings=findings,
        critical_count=crit_cnt,
        high_count=high_cnt,
        moderate_count=mod_cnt,
        info_count=info_cnt,
        pending_review_count=pending_cnt,
    )


@prescription_intelligence_router.get(
    "/patients/{patient_id}/medication-safety-findings",
    response_model=List[MedicationSafetyFindingResponse],
    summary="List Patient Medication Safety Findings",
)
async def list_patient_safety_findings(
    patient_id: str,
    severity: Optional[str] = Query(None),
    finding_type: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_token),
):
    svc = PrescriptionIntelligenceService(db)
    return await svc.get_medication_safety_findings(
        patient_id=patient_id,
        current_user=current_user,
        severity=severity,
        finding_type=finding_type,
        review_status=review_status,
    )


@prescription_intelligence_router.get(
    "/patients/{patient_id}/medication-safety-findings/{finding_id}",
    response_model=MedicationSafetyFindingResponse,
    summary="Get Specific Safety Finding",
)
async def get_patient_safety_finding(
    patient_id: str,
    finding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_token),
):
    svc = PrescriptionIntelligenceService(db)
    return await svc.get_medication_safety_finding(patient_id, finding_id, current_user)


# 5. Clinician Review Endpoint
@prescription_intelligence_router.post(
    "/medication-safety-findings/{finding_id}/review",
    response_model=MedicationSafetyFindingResponse,
    summary="Clinician Review & Verify Medication Safety Finding",
)
async def review_medication_safety_finding(
    finding_id: str,
    review_data: MedicationReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_token),
):
    client_ip = request.client.host if request.client else None
    svc = PrescriptionIntelligenceService(db)
    return await svc.review_medication_safety_finding(
        finding_id=finding_id,
        review_data=review_data,
        current_user=current_user,
        client_ip=client_ip,
    )


# 6. Safety Knowledge Base Rules Catalog
@prescription_intelligence_router.get(
    "/medication-rules",
    response_model=List[MedicationRuleResponse],
    summary="List All Configured Medication Safety Rules",
)
async def list_medication_rules(
    current_user: dict = Depends(get_current_user_token),
):
    return PrescriptionIntelligenceService.get_all_rules()
