import io
from typing import Any, Dict, List, Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    CLINICAL_STAFF_ROLES,
    UserRole,
    get_current_user_token,
    require_roles,
)
from app.modules.imaging.models import (
    FindingReviewStatusEnum,
    ImagingFinding,
    ImagingStudy,
    ModalityEnum,
)
from app.modules.imaging.schemas import (
    ImagingAnalysisResponse,
    ImagingExplainabilityResponse,
    ImagingFindingResponse,
    ImagingFindingReviewRequest,
    ImagingModelMetadataResponse,
    ImagingStudyDetailResponse,
    ImagingStudyResponse,
    ImagingTimelineResponse,
)
from app.modules.imaging.service import ImagingService
from app.modules.imaging.inference.model_registry import get_model_registry

router = APIRouter()


def _enforce_patient_isolation(token: dict, patient_id: str):
    """Enforces that patient role users can only access their own clinical records."""
    user_role = token.get("role")
    if user_role == UserRole.PATIENT.value:
        token_patient_id = token.get("patient_id")
        if token_patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access imaging records of another patient.",
            )


# ============================================================================
# PATIENT-SCOPED IMAGING STUDY ENDPOINTS
# ============================================================================

@router.post(
    "/patients/{patient_id}/imaging/studies",
    response_model=ImagingStudyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and register a new chest X-Ray / imaging study",
)
async def upload_patient_imaging_study(
    patient_id: str,
    file: UploadFile = File(...),
    modality: str = Form("XRAY"),
    body_part: str = Form("CHEST"),
    view_position: str = Form("PA"),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    _enforce_patient_isolation(token, patient_id)
    service = ImagingService(db)
    file_bytes = await file.read()

    study = await service.create_study_with_image(
        patient_id=patient_id,
        file_bytes=file_bytes,
        filename=file.filename or "uploaded_xray.png",
        content_type=file.content_type or "application/octet-stream",
        modality=modality,
        body_part=body_part,
        view_position=view_position,
        user_id=token.get("sub"),
    )
    return study


@router.get(
    "/patients/{patient_id}/imaging/studies",
    response_model=List[ImagingStudyResponse],
    summary="List all imaging studies for a patient",
)
async def list_patient_imaging_studies(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    _enforce_patient_isolation(token, patient_id)
    service = ImagingService(db)
    return await service.list_by_patient(patient_id)


@router.get(
    "/patients/{patient_id}/imaging/timeline",
    response_model=ImagingTimelineResponse,
    summary="Get longitudinal chest X-Ray timeline for patient",
)
async def get_patient_imaging_timeline(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    _enforce_patient_isolation(token, patient_id)
    service = ImagingService(db)
    return await service.get_patient_timeline(patient_id)


# ============================================================================
# STUDY DETAIL & ANALYSIS PIPELINE ENDPOINTS
# ============================================================================

@router.get(
    "/imaging/studies/{study_id}",
    response_model=ImagingStudyDetailResponse,
    summary="Get detailed imaging study with images and analyses",
)
async def get_imaging_study_detail(
    study_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    service = ImagingService(db)
    study = await service.get_by_id(study_id)
    _enforce_patient_isolation(token, study.patient_id)

    active_findings = []
    if study.analyses:
        latest = study.analyses[-1]
        active_findings = latest.findings

    return ImagingStudyDetailResponse(
        id=study.id,
        patient_id=study.patient_id,
        medical_document_id=study.medical_document_id,
        modality=study.modality,
        body_part=study.body_part,
        view_position=study.view_position,
        study_date=study.study_date,
        acquisition_date=study.acquisition_date,
        image_count=study.image_count,
        image_quality_status=study.image_quality_status,
        processing_status=study.processing_status,
        current_analysis_id=study.current_analysis_id,
        metadata_json=study.metadata_json,
        created_at=study.created_at,
        updated_at=study.updated_at,
        images=study.images,
        analyses=study.analyses,
        active_findings=active_findings,
    )


@router.post(
    "/imaging/studies/{study_id}/analyze",
    response_model=ImagingAnalysisResponse,
    summary="Trigger model inference analysis pipeline on an imaging study",
)
async def analyze_imaging_study(
    study_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    service = ImagingService(db)
    study = await service.get_by_id(study_id)
    _enforce_patient_isolation(token, study.patient_id)

    analysis = await service.run_analysis_pipeline(study_id, user_id=token.get("sub"))
    return analysis


@router.get(
    "/imaging/analyses/{analysis_id}",
    response_model=ImagingAnalysisResponse,
    summary="Get imaging analysis status and execution details",
)
async def get_imaging_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    service = ImagingService(db)
    return await service.get_analysis(analysis_id)


@router.get(
    "/imaging/analyses/{analysis_id}/findings",
    response_model=List[ImagingFindingResponse],
    summary="Get structured findings for an imaging analysis",
)
async def get_imaging_findings(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    service = ImagingService(db)
    return await service.get_findings(analysis_id, user_id=token.get("sub"))


@router.get(
    "/imaging/analyses/{analysis_id}/evidence",
    response_model=List[Dict[str, Any]],
    summary="Get verifiable evidence provenance items for an analysis",
)
async def get_imaging_analysis_evidence(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    service = ImagingService(db)
    return await service.get_analysis_evidence(analysis_id)


@router.get(
    "/imaging/analyses/{analysis_id}/explainability",
    response_model=ImagingExplainabilityResponse,
    summary="Get attention map and bounding box explainability metadata",
)
async def get_imaging_explainability(
    analysis_id: str,
    target_label: Optional[str] = Query(None, description="Optional finding label code for heatmap"),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    service = ImagingService(db)
    return await service.get_explainability(analysis_id, target_label=target_label, user_id=token.get("sub"))


# ============================================================================
# CLINICIAN REVIEW ENDPOINTS (RBAC RESTRICTED)
# ============================================================================

@router.post(
    "/imaging/findings/{finding_id}/review",
    response_model=ImagingFindingResponse,
    summary="Clinician review action (ACCEPT, MODIFY, REJECT) for an imaging finding",
    dependencies=[Depends(require_roles(CLINICAL_STAFF_ROLES))],
)
async def review_imaging_finding(
    finding_id: str,
    payload: ImagingFindingReviewRequest,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    service = ImagingService(db)
    return await service.review_finding(
        finding_id=finding_id,
        reviewer_id=token.get("sub", "clinician"),
        payload=payload,
    )


# ============================================================================
# MODEL REGISTRY & SECURE IMAGE STREAMING
# ============================================================================

@router.get(
    "/imaging/models",
    response_model=List[ImagingModelMetadataResponse],
    summary="List approved vision models from the model registry",
)
async def list_imaging_models(
    _token: dict = Depends(get_current_user_token),
):
    registry = get_model_registry()
    models = registry.list_models()
    return [
        ImagingModelMetadataResponse(
            model_id=m.model_id,
            version=m.version,
            modality=m.modality,
            framework=m.framework,
            input_size=m.input_size,
            supported_views=m.supported_views,
            labels=m.labels,
            training_dataset_reference=m.training_dataset_reference,
            intended_use=m.intended_use,
            limitations=m.limitations,
            threshold_version=m.threshold_version,
            calibration_status=m.calibration_status,
            calibration_version=m.calibration_version,
            is_production_ready=m.is_production_ready,
            model_sha256=m.model_sha256,
        )
        for m in models
    ]


@router.get(
    "/imaging/images/{image_id}/file",
    summary="Stream raw image bytes securely with patient isolation",
)
async def stream_imaging_file(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    from app.modules.imaging.models import ImagingImage
    image = await db.get(ImagingImage, image_id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image record not found.")

    study = await db.get(ImagingStudy, image.imaging_study_id)
    if study:
        _enforce_patient_isolation(token, study.patient_id)

    service = ImagingService(db)
    file_bytes = await service.storage.get_file_bytes(image.storage_key)
    return Response(content=file_bytes, media_type=image.mime_type or "image/png")


# ============================================================================
# BACKWARDS COMPATIBILITY SCAFFOLD ALIASES
# ============================================================================

@router.get("/imaging/patient/{patient_id}", response_model=List[ImagingStudyResponse], include_in_schema=False)
async def list_patient_imaging_studies_legacy(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    _enforce_patient_isolation(token, patient_id)
    service = ImagingService(db)
    return await service.list_by_patient(patient_id)
