import datetime
import hashlib
import time
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.core.queue import get_task_broker
from app.core.storage import get_storage_service

from app.modules.audit.models import AuditLog
from app.modules.patients.models import Patient
from app.modules.imaging.models import (
    FindingReviewStatusEnum,
    ImageQualityStatusEnum,
    ImagingAnalysis,
    ImagingFinding,
    ImagingImage,
    ImagingStudy,
    ModalityEnum,
    ProcessingStatusEnum,
)
from app.modules.imaging.validation import (
    MedicalImageValidationError,
    sanitize_filename,
    validate_and_inspect_image,
)
from app.modules.imaging.dicom import extract_phi_minimized_dicom_metadata
from app.modules.imaging.preprocessing.quality import assess_image_quality
from app.modules.imaging.preprocessing.pipeline import get_default_preprocessing_pipeline
from app.modules.imaging.inference.predictor import ImagingPredictor
from app.modules.imaging.inference.model_registry import get_model_registry
from app.modules.imaging.findings.builder import build_findings_from_inference
from app.modules.imaging.findings.safety import IMAGING_CDSS_DISCLAIMER, ImagingSafetyValidator
from app.modules.imaging.explainability.localization import get_explainability_engine
from app.modules.imaging.provenance.evidence import build_imaging_evidence_item
from app.modules.imaging.schemas import (
    ImagingExplainabilityResponse,
    ImagingFindingReviewRequest,
    ImagingStudyCreate,
    ImagingTimelineItem,
    ImagingTimelineResponse,
)


class ImagingService:
    """
    Main orchestration service for Medical Imaging Intelligence.
    Handles upload, validation, deterministic preprocessing, vision model inference,
    findings generation, clinician reviews, and longitudinal timelines.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = get_storage_service()
        self.broker = get_task_broker()
        self.model_registry = get_model_registry()

    async def create_study_with_image(
        self,
        patient_id: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        modality: str = "XRAY",
        body_part: str = "CHEST",
        view_position: Optional[str] = "PA",
        user_id: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> ImagingStudy:
        # 1. Verify Patient exists
        patient = await self.db.get(Patient, patient_id)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id}' not found.")

        # 2. Strict Image Validation
        clean_filename = sanitize_filename(filename)
        try:
            fmt, sha256_hash, width, height, bit_depth, color_space = validate_and_inspect_image(
                file_bytes, clean_filename, content_type
            )
        except Exception as e:
            # Audit rejection
            self.db.add(
                AuditLog(
                    actor_id=user_id,
                    action="IMAGING_REJECTED",
                    resource_type="IMAGING_IMAGE",
                    resource_id=clean_filename,
                    details={"patient_id": patient_id, "reason": str(e)},
                )
            )
            await self.db.commit()
            raise

        # 3. Quality Assessment Gate
        quality_status, quality_issues, quality_metrics = assess_image_quality(file_bytes)

        # 4. DICOM specific extraction if applicable
        dicom_meta = {}
        if fmt == "DICOM":
            dicom_meta = extract_phi_minimized_dicom_metadata(file_bytes)
            if dicom_meta.get("body_part"):
                body_part = dicom_meta["body_part"]
            if dicom_meta.get("view_position"):
                view_position = dicom_meta["view_position"]

        # 5. Secure Storage
        storage_key = f"imaging/{patient_id}/{sha256_hash}_{clean_filename}"
        await self.storage.save_file(file_bytes, storage_key, content_type=content_type)

        # 6. Database Records
        study = ImagingStudy(
            patient_id=patient_id,
            modality=modality.upper(),
            body_part=body_part.upper(),
            view_position=view_position.upper() if view_position else "PA",
            image_count=1,
            image_quality_status=quality_status,
            processing_status=ProcessingStatusEnum.QUEUED.value,
            metadata_json={
                **(metadata_json or {}),
                "quality_issues": quality_issues,
                "quality_metrics": quality_metrics,
                "dicom": dicom_meta,
            },
        )
        self.db.add(study)
        await self.db.flush()

        image = ImagingImage(
            imaging_study_id=study.id,
            storage_key=storage_key,
            original_filename=clean_filename,
            mime_type=content_type,
            file_size=len(file_bytes),
            sha256_hash=sha256_hash,
            width=width,
            height=height,
            bit_depth=bit_depth,
            color_space=color_space,
            orientation=view_position,
            metadata_json={"format": fmt, "quality_metrics": quality_metrics},
        )
        self.db.add(image)

        # 7. Audit Log
        self.db.add(
            AuditLog(
                actor_id=user_id,
                action="IMAGING_UPLOADED",
                resource_type="IMAGING_STUDY",
                resource_id=study.id,
                details={
                    "patient_id": patient_id,
                    "sha256": sha256_hash,
                    "filename": clean_filename,
                    "quality_status": quality_status,
                },
            )
        )
        await self.db.commit()
        await self.db.refresh(study)

        # 8. Dispatch Async Inference Task
        try:
            await self.broker.enqueue(
                "process_imaging_analysis",
                {"study_id": study.id, "user_id": user_id},
            )
        except Exception as e:
            logger.warning("Failed to enqueue background analysis task, will run synchronous fallback: %s", str(e))
            # Run synchronous pipeline
            await self.run_analysis_pipeline(study.id, user_id=user_id)
            await self.db.refresh(study)

        return study

    async def list_by_patient(self, patient_id: str) -> List[ImagingStudy]:
        stmt = (
            select(ImagingStudy)
            .where(ImagingStudy.patient_id == patient_id)
            .order_by(desc(ImagingStudy.study_date))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, study_id: str) -> ImagingStudy:
        stmt = (
            select(ImagingStudy)
            .where(ImagingStudy.id == study_id)
            .options(
                selectinload(ImagingStudy.images),
                selectinload(ImagingStudy.analyses).selectinload(ImagingAnalysis.findings),
            )
        )
        result = await self.db.execute(stmt)
        study = result.scalar_one_or_none()
        if not study:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ImagingStudy '{study_id}' not found.")
        return study

    async def run_analysis_pipeline(
        self, study_id: str, user_id: Optional[str] = None
    ) -> ImagingAnalysis:
        start_time = time.perf_counter()
        stmt = (
            select(ImagingStudy)
            .where(ImagingStudy.id == study_id)
            .options(selectinload(ImagingStudy.images))
        )
        result = await self.db.execute(stmt)
        study = result.scalar_one_or_none()
        if not study:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ImagingStudy '{study_id}' not found.")

        if not study.images:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ImagingStudy contains no images.")

        primary_image = study.images[0]
        study.processing_status = ProcessingStatusEnum.PREPROCESSING.value
        await self.db.commit()

        # Audit start
        self.db.add(
            AuditLog(
                actor_id=user_id,
                action="IMAGING_ANALYSIS_STARTED",
                resource_type="IMAGING_STUDY",
                resource_id=study.id,
                details={"patient_id": study.patient_id, "image_id": primary_image.id},
            )
        )
        await self.db.commit()

        try:
            # 1. Fetch file bytes from secure storage
            image_bytes = await self.storage.get_file_bytes(primary_image.storage_key)

            # 2. Quality Gate Check
            quality_status, quality_issues, quality_metrics = assess_image_quality(image_bytes)
            if quality_status == ImageQualityStatusEnum.QUALITY_REJECTED.value:
                study.processing_status = ProcessingStatusEnum.REJECTED.value
                study.image_quality_status = quality_status
                await self.db.commit()
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Image rejected by quality gate: {', '.join(quality_issues)}",
                )

            # 3. Deterministic Preprocessing
            pipeline = get_default_preprocessing_pipeline()
            processed_bytes, prep_meta, prep_matrix = pipeline.process(image_bytes)

            # 4. Model Inference
            study.processing_status = ProcessingStatusEnum.RUNNING.value
            await self.db.commit()

            predictor = ImagingPredictor()
            inference_result = predictor.run_inference(
                processed_bytes,
                prep_matrix,
                context={"custom_thresholds": None},
            )

            # 5. Persist Analysis Record
            analysis = ImagingAnalysis(
                imaging_study_id=study.id,
                model_id=inference_result.model_id,
                model_version=inference_result.model_version,
                preprocessing_version=inference_result.preprocessing_version,
                inference_version=inference_result.inference_version,
                threshold_version=inference_result.threshold_version,
                calibration_version=inference_result.calibration_metadata.calibration_version,
                status=ProcessingStatusEnum.COMPLETED.value,
                image_quality_status=quality_status,
                input_hash=prep_meta["input_hash"],
                output_json={
                    "raw_predictions": inference_result.raw_predictions,
                    "calibration": {
                        "method": inference_result.calibration_metadata.calibration_method,
                        "temperature": inference_result.calibration_metadata.temperature,
                        "dataset": inference_result.calibration_metadata.calibration_dataset,
                    },
                    "is_demo_mock": inference_result.is_demo_mock,
                },
                processing_time_ms=inference_result.inference_time_ms,
                completed_at=datetime.datetime.now(datetime.timezone.utc),
            )
            self.db.add(analysis)
            await self.db.flush()

            # 6. Build Structured Findings
            findings = build_findings_from_inference(
                analysis.id,
                inference_result.findings,
                inference_result.model_version,
            )
            for f in findings:
                self.db.add(f)

            # 7. Update Study
            study.current_analysis_id = analysis.id
            study.processing_status = ProcessingStatusEnum.COMPLETED.value
            study.image_quality_status = quality_status

            # 8. Audit Completion
            self.db.add(
                AuditLog(
                    actor_id=user_id,
                    action="IMAGING_ANALYSIS_COMPLETED",
                    resource_type="IMAGING_ANALYSIS",
                    resource_id=analysis.id,
                    details={
                        "patient_id": study.patient_id,
                        "findings_count": len(findings),
                        "model_version": analysis.model_version,
                    },
                )
            )
            await self.db.commit()
            
            stmt_reload = (
                select(ImagingAnalysis)
                .where(ImagingAnalysis.id == analysis.id)
                .options(selectinload(ImagingAnalysis.findings))
            )
            res_reload = await self.db.execute(stmt_reload)
            return res_reload.scalar_one()

        except Exception as e:
            study.processing_status = ProcessingStatusEnum.FAILED.value
            self.db.add(
                AuditLog(
                    actor_id=user_id,
                    action="IMAGING_ANALYSIS_FAILED",
                    resource_type="IMAGING_STUDY",
                    resource_id=study.id,
                    details={"error": str(e)},
                )
            )
            await self.db.commit()
            if isinstance(e, HTTPException):
                raise
            logger.error("Imaging analysis execution error: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Imaging analysis failed: {str(e)}",
            )

    async def get_analysis(self, analysis_id: str) -> ImagingAnalysis:
        stmt = (
            select(ImagingAnalysis)
            .where(ImagingAnalysis.id == analysis_id)
            .options(selectinload(ImagingAnalysis.findings))
        )
        result = await self.db.execute(stmt)
        analysis = result.scalar_one_or_none()
        if not analysis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ImagingAnalysis '{analysis_id}' not found.")
        return analysis

    async def get_findings(self, analysis_id: str, user_id: Optional[str] = None) -> List[ImagingFinding]:
        stmt = (
            select(ImagingFinding)
            .where(ImagingFinding.imaging_analysis_id == analysis_id)
            .order_by(desc(ImagingFinding.probability))
        )
        result = await self.db.execute(stmt)
        findings = list(result.scalars().all())

        # Audit finding view
        if user_id:
            self.db.add(
                AuditLog(
                    actor_id=user_id,
                    action="IMAGING_FINDING_VIEWED",
                    resource_type="IMAGING_ANALYSIS",
                    resource_id=analysis_id,
                    details={"count": len(findings)},
                )
            )
            await self.db.commit()

        return findings

    async def review_finding(
        self,
        finding_id: str,
        reviewer_id: str,
        payload: ImagingFindingReviewRequest,
    ) -> ImagingFinding:
        finding = await self.db.get(ImagingFinding, finding_id)
        if not finding:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ImagingFinding '{finding_id}' not found.")

        # Immutability Guarantee: Original model probability, threshold, and localization remain unmodified
        finding.review_status = payload.review_status.value
        finding.reviewed_by = reviewer_id
        finding.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
        finding.clinician_comment = payload.clinician_comment
        if payload.modified_severity:
            finding.severity = payload.modified_severity

        # Audit review action
        action_map = {
            FindingReviewStatusEnum.ACCEPTED: "IMAGING_FINDING_ACCEPTED",
            FindingReviewStatusEnum.MODIFIED: "IMAGING_FINDING_MODIFIED",
            FindingReviewStatusEnum.REJECTED: "IMAGING_FINDING_REJECTED",
        }
        action_name = action_map.get(payload.review_status, "IMAGING_FINDING_REVIEWED")

        self.db.add(
            AuditLog(
                actor_id=reviewer_id,
                action=action_name,
                resource_type="IMAGING_FINDING",
                resource_id=finding.id,
                details={
                    "finding_code": finding.finding_code,
                    "review_status": finding.review_status,
                    "comment": finding.clinician_comment,
                },
            )
        )
        await self.db.commit()
        await self.db.refresh(finding)
        return finding

    async def get_explainability(
        self, analysis_id: str, target_label: Optional[str] = None, user_id: Optional[str] = None
    ) -> ImagingExplainabilityResponse:
        analysis = await self.get_analysis(analysis_id)
        study = await self.db.get(ImagingStudy, analysis.imaging_study_id)
        if not study:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated study not found.")

        # Determine target label (highest probability finding if none specified)
        if not target_label:
            if analysis.findings:
                sorted_f = sorted(analysis.findings, key=lambda x: x.probability, reverse=True)
                target_label = sorted_f[0].finding_code
            else:
                target_label = "CARDIOMEGALY"

        engine = get_explainability_engine()
        # Find finding probability
        prob = 0.5
        for f in analysis.findings:
            if f.finding_code == target_label:
                prob = f.probability
                break

        res = engine.generate_heatmap(b"", target_label, prob, analysis.model_version)

        # Audit explainability view
        if user_id:
            self.db.add(
                AuditLog(
                    actor_id=user_id,
                    action="EXPLAINABILITY_VIEWED",
                    resource_type="IMAGING_ANALYSIS",
                    resource_id=analysis.id,
                    details={"target_label": target_label, "method": res.method},
                )
            )
            await self.db.commit()

        return ImagingExplainabilityResponse(
            analysis_id=analysis.id,
            method=res.method,
            model_version=res.model_version,
            target_label=res.target_label,
            heatmap_grid=res.heatmap_grid,
            localization_boxes=res.localization_boxes,
            disclaimer=res.disclaimer,
            generated_at=res.generated_at,
        )

    async def get_patient_timeline(self, patient_id: str) -> ImagingTimelineResponse:
        stmt = (
            select(ImagingStudy)
            .where(ImagingStudy.patient_id == patient_id)
            .options(
                selectinload(ImagingStudy.analyses).selectinload(ImagingAnalysis.findings)
            )
            .order_by(desc(ImagingStudy.study_date))
        )
        result = await self.db.execute(stmt)
        studies = list(result.scalars().all())

        timeline_items: List[ImagingTimelineItem] = []
        for s in studies:
            latest_analysis = s.analyses[-1] if s.analyses else None
            findings_list = latest_analysis.findings if latest_analysis else []

            review_counts = {"PENDING": 0, "ACCEPTED": 0, "MODIFIED": 0, "REJECTED": 0}
            key_findings = []
            for f in findings_list:
                review_counts[f.review_status] = review_counts.get(f.review_status, 0) + 1
                if f.probability >= f.model_threshold:
                    key_findings.append({
                        "finding_code": f.finding_code,
                        "finding_name": f.finding_name,
                        "probability": f.probability,
                        "threshold": f.model_threshold,
                        "review_status": f.review_status,
                    })

            timeline_items.append(
                ImagingTimelineItem(
                    study_id=s.id,
                    study_date=s.study_date,
                    modality=s.modality,
                    body_part=s.body_part,
                    view_position=s.view_position,
                    analysis_id=latest_analysis.id if latest_analysis else None,
                    model_version=latest_analysis.model_version if latest_analysis else None,
                    processing_status=s.processing_status,
                    image_quality_status=s.image_quality_status,
                    findings_count=len(findings_list),
                    key_findings=key_findings,
                    review_status_summary=review_counts,
                )
            )

        return ImagingTimelineResponse(
            patient_id=patient_id,
            total_studies=len(studies),
            timeline=timeline_items,
            cdss_disclaimer=IMAGING_CDSS_DISCLAIMER,
        )

    async def get_analysis_evidence(self, analysis_id: str) -> List[Dict[str, Any]]:
        analysis = await self.get_analysis(analysis_id)
        study = await self.db.get(ImagingStudy, analysis.imaging_study_id)
        evidence_items = []
        for f in analysis.findings:
            ev = build_imaging_evidence_item(f, study, analysis)
            evidence_items.append(ev.model_dump())
        return evidence_items


async def process_imaging_analysis_task(study_id: str, user_id: Optional[str] = None):
    """Entry point for async background worker."""
    async with AsyncSessionLocal() as session:
        service = ImagingService(session)
        await service.run_analysis_pipeline(study_id, user_id=user_id)
