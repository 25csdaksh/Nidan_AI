import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.clinical_intelligence.models import (
    ClinicalAnalysis,
    ClinicalFinding,
    FindingTypeEnum,
    FindingStatusEnum,
    FindingSeverityEnum,
    FindingReviewStatusEnum,
    ClinicalObservation,
    LongitudinalAnalysis,
    LongitudinalTrend,
    LongitudinalSummarySection,
    LongitudinalReviewNote,
    TrendDirectionEnum,
    TrendStatusEnum,
    AbnormalityDynamicsEnum,
    SummarySectionTypeEnum,
)
from app.modules.clinical_intelligence.schemas import (
    FindingReviewRequest,
    PatientLongitudinalResponse,
    LongitudinalAnalyteSeries,
    LongitudinalDataPoint,
    LongitudinalAnalysisRequest,
    LongitudinalAnalysisResponse,
    LongitudinalTrendResponse,
    LongitudinalSummarySectionResponse,
    LongitudinalReviewNoteCreate,
    LongitudinalReviewNoteResponse,
    PatientTimelineResponse,
    TimelineVisitGroup,
    TimelineObservationItem,
)
from app.modules.clinical_intelligence.engine.evaluator import ClinicalEvaluationContextBuilder
from app.modules.clinical_intelligence.engine.finding_builder import FindingBuilder
from app.modules.clinical_intelligence.engine.rule_engine import ClinicalRuleEngine
from app.modules.clinical_intelligence.longitudinal.date_resolver import ObservationDateResolver
from app.modules.clinical_intelligence.longitudinal.trend_engine import TrendEngine
from app.modules.clinical_intelligence.longitudinal.dynamics_engine import AbnormalityDynamicsEngine
from app.modules.clinical_intelligence.longitudinal.panel_completeness import PanelCompletenessAnalyzer
from app.modules.clinical_intelligence.longitudinal.comparison_engine import CrossVisitComparisonEngine, CrossVisitComparisonResult
from app.modules.clinical_intelligence.longitudinal.summary_engine import LongitudinalSummaryEngine
from app.modules.medical_documents.models import (
    MedicalDocument,
    DocumentExtraction,
    DocumentExtractionEntity,
)
from app.modules.patients.models import Patient
from app.modules.audit.service import AuditService
from app.modules.audit.schemas import AuditLogCreate


class ClinicalIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.context_builder = ClinicalEvaluationContextBuilder()
        self.rule_engine = ClinicalRuleEngine()
        self.audit_service = AuditService(db) if db else None

    # ---------------------------------------------------------------------
    # Phase 3: Single-Document Clinical Intelligence Analysis
    # ---------------------------------------------------------------------

    async def run_clinical_analysis(
        self,
        document_id: str,
        force_reanalyze: bool = False,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ClinicalAnalysis:
        """Run deterministic clinical intelligence analysis on extracted lab entities."""
        # 1. Fetch Document and extraction
        doc_stmt = select(MedicalDocument).where(MedicalDocument.id == document_id)
        doc_res = await self.db.execute(doc_stmt)
        doc = doc_res.scalars().first()
        if not doc:
            raise ValueError(f"Medical document '{document_id}' not found.")

        # Fetch latest completed extraction
        ext_stmt = (
            select(DocumentExtraction)
            .where(
                and_(
                    DocumentExtraction.document_id == document_id,
                    DocumentExtraction.status == "COMPLETED",
                )
            )
            .order_by(desc(DocumentExtraction.extraction_version))
            .limit(1)
        )
        ext_res = await self.db.execute(ext_stmt)
        extraction = ext_res.scalars().first()
        if not extraction:
            raise ValueError(f"No completed extraction found for document '{document_id}'. Run extraction first.")

        # Idempotency check
        existing_analysis_stmt = (
            select(ClinicalAnalysis)
            .options(selectinload(ClinicalAnalysis.findings))
            .where(
                and_(
                    ClinicalAnalysis.document_id == document_id,
                    ClinicalAnalysis.extraction_id == extraction.id,
                )
            )
            .order_by(desc(ClinicalAnalysis.analysis_version))
            .limit(1)
        )
        existing_analysis_res = await self.db.execute(existing_analysis_stmt)
        existing_analysis = existing_analysis_res.scalars().first()

        if existing_analysis and not force_reanalyze:
            # Sync observations if not yet synced
            await self.sync_clinical_observations_from_document(document_id, doc.patient_id)
            return existing_analysis

        # 2. Fetch Entities & Patient
        entities_stmt = select(DocumentExtractionEntity).where(
            DocumentExtractionEntity.extraction_id == extraction.id
        )
        entities_res = await self.db.execute(entities_stmt)
        entities = list(entities_res.scalars().all())

        patient = None
        if doc.patient_id:
            p_stmt = select(Patient).where(Patient.id == doc.patient_id)
            p_res = await self.db.execute(p_stmt)
            patient = p_res.scalars().first()

        # Audit started
        if self.audit_service:
            await self.audit_service.log_event(
                AuditLogCreate(
                    actor_id=actor_id,
                    action="CLINICAL_ANALYSIS_STARTED",
                    resource_type="medical_documents",
                    resource_id=document_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "document_id": document_id,
                        "extraction_id": extraction.id,
                        "entity_count": len(entities),
                    },
                )
            )

        # 3. Build context & evaluate rules
        context = self.context_builder.build_context(
            document=doc,
            extraction=extraction,
            entities=entities,
            patient=patient,
        )

        rule_results = self.rule_engine.evaluate_all(context)

        # 4. Create Analysis record
        analysis_id = str(uuid.uuid4())
        analysis = ClinicalAnalysis(
            id=analysis_id,
            patient_id=doc.patient_id or "UNKNOWN",
            document_id=document_id,
            extraction_id=extraction.id,
            analysis_version=1 if not existing_analysis else existing_analysis.analysis_version + 1,
            rule_set_version="1.0.0",
            reference_range_version="2026.1",
            status="COMPLETED",
            findings_count=0,
            abnormal_count=0,
            critical_count=0,
            pattern_count=0,
            summary_metadata={
                "analyte_count": len(entities),
                "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.db.add(analysis)

        # 5. Build and attach findings
        findings_to_persist = []
        abnormal_cnt = 0
        critical_cnt = 0
        pattern_cnt = 0

        for r_res in rule_results:
            matching_entity_id = None
            if r_res.evidence and len(r_res.evidence) == 1:
                matching_entity_id = r_res.evidence[0].get("entity_id")

            finding = FindingBuilder.build_finding(
                result=r_res,
                analysis_id=analysis_id,
                patient_id=doc.patient_id or "UNKNOWN",
                document_id=document_id,
                extraction_id=extraction.id,
                entity_id=matching_entity_id,
            )
            findings_to_persist.append(finding)
            self.db.add(finding)

            if finding.status in (FindingStatusEnum.LOW.value, FindingStatusEnum.HIGH.value):
                abnormal_cnt += 1
            if finding.status in (FindingStatusEnum.CRITICAL_LOW.value, FindingStatusEnum.CRITICAL_HIGH.value):
                critical_cnt += 1
            if finding.finding_type == FindingTypeEnum.PATTERN.value:
                pattern_cnt += 1

        analysis.findings_count = len(findings_to_persist)
        analysis.abnormal_count = abnormal_cnt
        analysis.critical_count = critical_cnt
        analysis.pattern_count = pattern_cnt

        await self.db.commit()

        # Sync normalized clinical observations for Phase 4 longitudinal timeline
        await self.sync_clinical_observations_from_document(document_id, doc.patient_id)

        # Audit completed
        if self.audit_service:
            await self.audit_service.log_event(
                AuditLogCreate(
                    actor_id=actor_id,
                    action="CLINICAL_ANALYSIS_COMPLETED",
                    resource_type="medical_documents",
                    resource_id=document_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "analysis_id": analysis.id,
                        "findings_count": analysis.findings_count,
                        "abnormal_count": abnormal_cnt,
                        "critical_count": critical_cnt,
                        "pattern_count": pattern_cnt,
                    },
                )
            )

        # Re-fetch with loaded findings
        refetched_stmt = (
            select(ClinicalAnalysis)
            .options(selectinload(ClinicalAnalysis.findings))
            .where(ClinicalAnalysis.id == analysis.id)
        )
        refetched_res = await self.db.execute(refetched_stmt)
        return refetched_res.scalars().first()

    async def get_document_analysis(self, document_id: str) -> Optional[ClinicalAnalysis]:
        stmt = (
            select(ClinicalAnalysis)
            .options(selectinload(ClinicalAnalysis.findings))
            .where(ClinicalAnalysis.document_id == document_id)
            .order_by(desc(ClinicalAnalysis.created_at))
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_findings(
        self,
        document_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        finding_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ClinicalFinding]:
        stmt = select(ClinicalFinding)
        if document_id:
            stmt = stmt.where(ClinicalFinding.document_id == document_id)
        if patient_id:
            stmt = stmt.where(ClinicalFinding.patient_id == patient_id)
        if finding_type:
            stmt = stmt.where(ClinicalFinding.finding_type == finding_type)
        if status:
            stmt = stmt.where(ClinicalFinding.status == status)
        stmt = stmt.order_by(desc(ClinicalFinding.created_at)).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def review_finding(
        self,
        finding_id: str,
        review_data: FindingReviewRequest,
        reviewer_id: str,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ClinicalFinding:
        stmt = select(ClinicalFinding).where(ClinicalFinding.id == finding_id)
        res = await self.db.execute(stmt)
        finding = res.scalars().first()
        if not finding:
            raise ValueError(f"Clinical finding '{finding_id}' not found.")

        orig_status = finding.review_status
        finding.review_status = review_data.review_status.value
        finding.reviewed_by = reviewer_id
        finding.reviewed_at = datetime.now(timezone.utc)
        finding.reviewer_notes = review_data.reviewer_notes

        if review_data.modified_title:
            finding.title = review_data.modified_title
        if review_data.modified_explanation:
            finding.explanation = review_data.modified_explanation

        # Also update doctor verified status on corresponding observation if present
        if finding.entity_id:
            obs_stmt = select(ClinicalObservation).where(ClinicalObservation.entity_id == finding.entity_id)
            obs_res = await self.db.execute(obs_stmt)
            obs = obs_res.scalars().first()
            if obs:
                obs.is_doctor_verified = (review_data.review_status == FindingReviewStatusEnum.ACCEPTED)

        await self.db.commit()
        await self.db.refresh(finding)

        # Audit finding review
        if self.audit_service:
            await self.audit_service.log_event(
                AuditLogCreate(
                    actor_id=actor_id or reviewer_id,
                    action="CLINICAL_FINDING_REVIEWED",
                    resource_type="clinical_findings",
                    resource_id=finding_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "finding_id": finding_id,
                        "previous_status": orig_status,
                        "new_status": finding.review_status,
                        "reviewer_id": reviewer_id,
                    },
                )
            )

        return finding

    async def get_patient_longitudinal_series(self, patient_id: str) -> PatientLongitudinalResponse:
        """Aggregate chronological observations for key clinical markers."""
        stmt = (
            select(ClinicalFinding, MedicalDocument.created_at)
            .join(MedicalDocument, ClinicalFinding.document_id == MedicalDocument.id)
            .where(
                and_(
                    ClinicalFinding.patient_id == patient_id,
                    ClinicalFinding.finding_type == FindingTypeEnum.ABNORMAL_LAB.value,
                    ClinicalFinding.normalized_value.is_not(None),
                )
            )
            .order_by(MedicalDocument.created_at.asc())
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        analyte_dict: Dict[str, List[LongitudinalDataPoint]] = {}
        analyte_units: Dict[str, Optional[str]] = {}

        for finding, doc_date in rows:
            aname = finding.analyte or "Unknown"
            if aname not in analyte_dict:
                analyte_dict[aname] = []
                analyte_units[aname] = finding.unit

            date_str = doc_date.strftime("%Y-%m-%d") if doc_date else "Unknown"
            analyte_dict[aname].append(
                LongitudinalDataPoint(
                    date=date_str,
                    document_id=finding.document_id,
                    value=finding.normalized_value,
                    unit=finding.unit,
                    status=finding.status,
                    severity=finding.severity,
                )
            )

        series_list = [
            LongitudinalAnalyteSeries(
                analyte=aname,
                unit=analyte_units.get(aname),
                data_points=pts,
            )
            for aname, pts in analyte_dict.items()
        ]

        return PatientLongitudinalResponse(
            patient_id=patient_id,
            analytes=series_list,
            total_observations=len(rows),
        )

    def get_active_rules_metadata(self) -> List[Dict[str, Any]]:
        return self.rule_engine.get_rule_metadata()

    # ---------------------------------------------------------------------
    # Phase 4: Longitudinal Observations Normalization & Synchronization
    # ---------------------------------------------------------------------

    async def sync_clinical_observations_from_document(
        self,
        document_id: str,
        patient_id: Optional[str] = None,
    ) -> List[ClinicalObservation]:
        """
        Normalizes and synchronizes document extraction entities into clinical_observations
        with prioritized observation date resolution and deduplication.
        """
        # Fetch document
        doc_stmt = select(MedicalDocument).where(MedicalDocument.id == document_id)
        doc_res = await self.db.execute(doc_stmt)
        doc = doc_res.scalars().first()
        if not doc:
            return []

        eff_patient_id = patient_id or doc.patient_id or "UNKNOWN"

        # Fetch latest completed extraction
        ext_stmt = (
            select(DocumentExtraction)
            .where(
                and_(
                    DocumentExtraction.document_id == document_id,
                    DocumentExtraction.status == "COMPLETED",
                )
            )
            .order_by(desc(DocumentExtraction.extraction_version))
            .limit(1)
        )
        ext_res = await self.db.execute(ext_stmt)
        extraction = ext_res.scalars().first()
        if not extraction:
            return []

        # Resolve observation date
        date_res = ObservationDateResolver.resolve_date(
            document_text=extraction.raw_text or "",
            document_metadata=doc.metadata_json or {},
            document_created_at=doc.created_at,
        )

        # Fetch entities
        ent_stmt = select(DocumentExtractionEntity).where(
            DocumentExtractionEntity.extraction_id == extraction.id
        )
        ent_res = await self.db.execute(ent_stmt)
        entities = list(ent_res.scalars().all())

        # Fetch findings for status/reference lookup
        find_stmt = select(ClinicalFinding).where(ClinicalFinding.extraction_id == extraction.id)
        find_res = await self.db.execute(find_stmt)
        findings_map = {f.entity_id: f for f in find_res.scalars().all() if f.entity_id}

        synced_observations = []
        for ent in entities:
            if not ent.canonical_name or ent.numeric_value is None:
                continue

            # Check if observation already exists for this entity_id
            existing_obs_stmt = select(ClinicalObservation).where(
                ClinicalObservation.entity_id == ent.id
            )
            existing_obs_res = await self.db.execute(existing_obs_stmt)
            obs = existing_obs_res.scalars().first()

            finding = findings_map.get(ent.id)
            tech_status = finding.status if finding else FindingStatusEnum.NORMAL.value
            is_verified = (finding.review_status == FindingReviewStatusEnum.ACCEPTED.value) if finding else False

            ref_min = ent.reference_min
            ref_max = ent.reference_max
            unit = ent.normalized_unit or ent.original_unit

            if not obs:
                obs = ClinicalObservation(
                    id=str(uuid.uuid4()),
                    patient_id=eff_patient_id,
                    document_id=document_id,
                    extraction_id=extraction.id,
                    entity_id=ent.id,
                    analyte=ent.raw_name,
                    canonical_name=ent.canonical_name,
                    value=str(ent.value_text),
                    normalized_value=ent.numeric_value,
                    unit=unit,
                    observation_date=date_res.resolved_date,
                    observation_date_source=date_res.source,
                    date_confidence=date_res.confidence,
                    document_date=doc.created_at,
                    technical_status=tech_status,
                    reference_min=ref_min,
                    reference_max=ref_max,
                    reference_source="REPORT",
                    extraction_confidence=ent.confidence or 1.0,
                    finding_confidence=finding.confidence if finding else 1.0,
                    source_text=ent.source_text or ent.value_text,
                    page_number=ent.page_number or 1,
                    is_doctor_verified=is_verified,
                )
                self.db.add(obs)
            else:
                # Update attributes
                obs.observation_date = date_res.resolved_date
                obs.observation_date_source = date_res.source
                obs.date_confidence = date_res.confidence
                obs.technical_status = tech_status
                obs.is_doctor_verified = is_verified
                obs.normalized_value = ent.numeric_value
                obs.unit = unit
                if ref_min is not None:
                    obs.reference_min = ref_min
                if ref_max is not None:
                    obs.reference_max = ref_max

            synced_observations.append(obs)

        await self.db.commit()
        return synced_observations

    # ---------------------------------------------------------------------
    # Phase 4: Patient Longitudinal Timeline API
    # ---------------------------------------------------------------------

    async def get_patient_timeline(
        self,
        patient_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        analyte: Optional[str] = None,
        panel: Optional[str] = None,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> PatientTimelineResponse:
        """
        Returns all observations grouped chronologically by visit/document for a patient.
        """
        # Ensure all existing documents for this patient are synced
        doc_stmt = select(MedicalDocument).where(MedicalDocument.patient_id == patient_id)
        doc_res = await self.db.execute(doc_stmt)
        docs = doc_res.scalars().all()
        for d in docs:
            await self.sync_clinical_observations_from_document(d.id, patient_id)

        # Build query for observations
        stmt = (
            select(ClinicalObservation, MedicalDocument.document_type)
            .join(MedicalDocument, ClinicalObservation.document_id == MedicalDocument.id)
            .where(ClinicalObservation.patient_id == patient_id)
        )

        if start_date:
            try:
                s_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                stmt = stmt.where(ClinicalObservation.observation_date >= s_dt)
            except Exception:
                pass

        if end_date:
            try:
                e_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                stmt = stmt.where(ClinicalObservation.observation_date <= e_dt)
            except Exception:
                pass

        if analyte:
            stmt = stmt.where(
                (ClinicalObservation.analyte.ilike(f"%{analyte}%")) |
                (ClinicalObservation.canonical_name.ilike(f"%{analyte}%"))
            )

        if status:
            stmt = stmt.where(ClinicalObservation.technical_status == status)

        if document_type:
            stmt = stmt.where(MedicalDocument.document_type == document_type)

        stmt = stmt.order_by(asc(ClinicalObservation.observation_date), asc(ClinicalObservation.created_at))
        res = await self.db.execute(stmt)
        rows = res.all()

        # Group by document_id (representing a distinct visit/report)
        visits_dict: Dict[str, TimelineVisitGroup] = {}
        total_obs = len(rows)

        for obs, dtype in rows:
            doc_id = obs.document_id
            v_date = obs.observation_date.strftime("%Y-%m-%d") if obs.observation_date else "Unknown Date"

            if doc_id not in visits_dict:
                visits_dict[doc_id] = TimelineVisitGroup(
                    document_id=doc_id,
                    document_type=dtype or "LAB_REPORT",
                    visit_date=v_date,
                    date_source=obs.observation_date_source,
                    observations=[],
                )

            visits_dict[doc_id].observations.append(
                TimelineObservationItem(
                    observation_id=obs.id,
                    document_id=obs.document_id,
                    analyte=obs.analyte,
                    value=obs.value,
                    numeric_value=obs.normalized_value,
                    unit=obs.unit,
                    status=obs.technical_status,
                    reference_min=obs.reference_min,
                    reference_max=obs.reference_max,
                    observation_date=v_date if obs.observation_date else None,
                    date_source=obs.observation_date_source,
                    date_confidence=obs.date_confidence,
                    is_doctor_verified=obs.is_doctor_verified,
                )
            )

        visit_list = list(visits_dict.values())
        return PatientTimelineResponse(
            patient_id=patient_id,
            total_visits=len(visit_list),
            total_observations=total_obs,
            visits=visit_list,
        )

    # ---------------------------------------------------------------------
    # Phase 4: Analyte Trends Engine
    # ---------------------------------------------------------------------

    async def get_patient_trends(
        self,
        patient_id: str,
        analyte: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Runs deterministic TrendEngine on patient observations.
        """
        # Ensure sync
        doc_stmt = select(MedicalDocument).where(MedicalDocument.patient_id == patient_id)
        doc_res = await self.db.execute(doc_stmt)
        for d in doc_res.scalars().all():
            await self.sync_clinical_observations_from_document(d.id, patient_id)

        stmt = select(ClinicalObservation).where(ClinicalObservation.patient_id == patient_id)
        if analyte:
            stmt = stmt.where(
                (ClinicalObservation.analyte.ilike(f"%{analyte}%")) |
                (ClinicalObservation.canonical_name.ilike(f"%{analyte}%"))
            )
        stmt = stmt.order_by(asc(ClinicalObservation.observation_date), asc(ClinicalObservation.created_at))

        res = await self.db.execute(stmt)
        observations = list(res.scalars().all())

        trend_results = TrendEngine.evaluate_trends(observations)
        return [tr.model_dump() for tr in trend_results]

    # ---------------------------------------------------------------------
    # Phase 4: Longitudinal Cross-Visit Comparison Engine
    # ---------------------------------------------------------------------

    async def compare_patient_visits(
        self,
        patient_id: str,
        visit_a_doc_id: str,
        visit_b_doc_id: str,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> CrossVisitComparisonResult:
        """
        Runs CrossVisitComparisonEngine comparing two distinct visits.
        """
        # Sync both documents
        await self.sync_clinical_observations_from_document(visit_a_doc_id, patient_id)
        await self.sync_clinical_observations_from_document(visit_b_doc_id, patient_id)

        stmt = select(ClinicalObservation).where(
            and_(
                ClinicalObservation.patient_id == patient_id,
                ClinicalObservation.document_id.in_([visit_a_doc_id, visit_b_doc_id]),
            )
        ).order_by(asc(ClinicalObservation.observation_date))

        res = await self.db.execute(stmt)
        observations = list(res.scalars().all())

        visit_a_obs = [o for o in observations if o.document_id == visit_a_doc_id]
        visit_b_obs = [o for o in observations if o.document_id == visit_b_doc_id]

        comparison = CrossVisitComparisonEngine.compare_visits(
            patient_id=patient_id,
            visit_a_doc_id=visit_a_doc_id,
            visit_a_obs=visit_a_obs,
            visit_b_doc_id=visit_b_doc_id,
            visit_b_obs=visit_b_obs,
        )

        if self.audit_service:
            await self.audit_service.log_event(
                AuditLogCreate(
                    actor_id=actor_id,
                    action="LONGITUDINAL_COMPARISON_VIEWED",
                    resource_type="patients",
                    resource_id=patient_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "visit_a_doc_id": visit_a_doc_id,
                        "visit_b_doc_id": visit_b_doc_id,
                        "compared_analytes_count": len(comparison.items),
                    },
                )
            )

        return comparison

    # ---------------------------------------------------------------------
    # Phase 4: Comprehensive Multi-Visit Longitudinal Analysis & Summary
    # ---------------------------------------------------------------------

    async def run_longitudinal_analysis(
        self,
        patient_id: str,
        request_data: Optional[LongitudinalAnalysisRequest] = None,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> LongitudinalAnalysis:
        """
        Runs comprehensive multi-visit longitudinal analysis, evaluates trend dynamics,
        generates auditable summary sections with provenance, and persists immutable results.
        """
        # 1. Sync all documents for patient
        doc_stmt = select(MedicalDocument).where(MedicalDocument.patient_id == patient_id)
        doc_res = await self.db.execute(doc_stmt)
        docs = list(doc_res.scalars().all())
        for d in docs:
            await self.sync_clinical_observations_from_document(d.id, patient_id)

        # Audit started
        if self.audit_service:
            await self.audit_service.log_event(
                AuditLogCreate(
                    actor_id=actor_id,
                    action="LONGITUDINAL_ANALYSIS_STARTED",
                    resource_type="patients",
                    resource_id=patient_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "patient_id": patient_id,
                        "total_documents": len(docs),
                    },
                )
            )

        # 2. Fetch observations
        stmt = select(ClinicalObservation).where(ClinicalObservation.patient_id == patient_id)
        if request_data and request_data.analytes:
            stmt = stmt.where(ClinicalObservation.canonical_name.in_(request_data.analytes))

        if request_data and request_data.start_date:
            try:
                s_dt = datetime.fromisoformat(request_data.start_date.replace("Z", "+00:00"))
                stmt = stmt.where(ClinicalObservation.observation_date >= s_dt)
            except Exception:
                pass

        if request_data and request_data.end_date:
            try:
                e_dt = datetime.fromisoformat(request_data.end_date.replace("Z", "+00:00"))
                stmt = stmt.where(ClinicalObservation.observation_date <= e_dt)
            except Exception:
                pass

        stmt = stmt.order_by(asc(ClinicalObservation.observation_date), asc(ClinicalObservation.created_at))
        res = await self.db.execute(stmt)
        observations = list(res.scalars().all())

        # 3. Deterministic Engines
        trends = TrendEngine.evaluate_trends(observations)
        dynamics_report = AbnormalityDynamicsEngine.evaluate_dynamics(observations)
        panel_results = PanelCompletenessAnalyzer.analyze_panel_completeness(observations)

        # Generate summary sections
        generated_sections = LongitudinalSummaryEngine.generate_summary_sections(
            patient_id=patient_id,
            observations=observations,
            trends=trends,
            dynamics=dynamics_report,
            panel_results=panel_results,
        )

        # Determine start and end dates
        valid_dates = [obs.observation_date for obs in observations if obs.observation_date]
        start_date = min(valid_dates) if valid_dates else None
        end_date = max(valid_dates) if valid_dates else None
        unique_doc_ids = list(set(obs.document_id for obs in observations))

        # Check existing analysis version
        last_analysis_stmt = (
            select(LongitudinalAnalysis)
            .where(LongitudinalAnalysis.patient_id == patient_id)
            .order_by(desc(LongitudinalAnalysis.analysis_version))
            .limit(1)
        )
        last_analysis_res = await self.db.execute(last_analysis_stmt)
        last_analysis = last_analysis_res.scalars().first()
        next_version = (last_analysis.analysis_version + 1) if last_analysis else 1

        # 4. Create Analysis record
        analysis_id = str(uuid.uuid4())
        full_summary_text = "\n\n".join(
            f"### {sec.title}\n{sec.generated_text}" for sec in generated_sections
        )

        analysis = LongitudinalAnalysis(
            id=analysis_id,
            patient_id=patient_id,
            analysis_version=next_version,
            trend_rule_version="1.0.0",
            summary_version="1.0.0",
            observation_count=len(observations),
            visit_count=len(unique_doc_ids),
            start_date=start_date,
            end_date=end_date,
            summary_text=full_summary_text,
            metadata_json={
                "dynamics_summary": dynamics_report.summary_counts,
                "panel_warnings_count": len(dynamics_report.data_quality_warnings),
            },
        )
        self.db.add(analysis)

        # 5. Attach Trends
        dynamics_map = {item.canonical_name: item for item in dynamics_report.items}
        for tr in trends:
            dyn_item = dynamics_map.get(tr.canonical_name)
            dyn_class = dyn_item.classification if dyn_item else AbnormalityDynamicsEnum.NORMAL.value
            persist_cnt = dyn_item.persistence_count if dyn_item else 0

            t_record = LongitudinalTrend(
                id=str(uuid.uuid4()),
                analysis_id=analysis_id,
                patient_id=patient_id,
                analyte=tr.analyte,
                canonical_name=tr.canonical_name,
                unit=tr.unit,
                direction=str(tr.direction),
                trend_status=str(tr.trend_status),
                dynamics_classification=str(dyn_class),
                observation_count=tr.observation_count,
                first_value=tr.first_value,
                last_value=tr.last_value,
                first_date=tr.first_date,
                last_date=tr.last_date,
                absolute_change=tr.absolute_change,
                percentage_change=tr.percentage_change,
                persistence_count=persist_cnt,
                history_points=tr.history_points,
            )
            self.db.add(t_record)

        # 6. Attach Summary Sections
        for sec in generated_sections:
            sec_record = LongitudinalSummarySection(
                id=str(uuid.uuid4()),
                analysis_id=analysis_id,
                patient_id=patient_id,
                section_type=str(sec.section_type),
                title=sec.title,
                generated_text=sec.generated_text,
                evidence_ids=sec.evidence_ids,
                source_documents=sec.source_documents,
                source_entities=sec.source_entities,
                generated_by=sec.generated_by,
                generation_version=sec.generation_version,
                safety_validation_status=sec.safety_validation_status,
            )
            self.db.add(sec_record)

        await self.db.commit()

        # Audit completed
        if self.audit_service:
            await self.audit_service.log_event(
                AuditLogCreate(
                    actor_id=actor_id,
                    action="LONGITUDINAL_ANALYSIS_COMPLETED",
                    resource_type="patients",
                    resource_id=patient_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "analysis_id": analysis_id,
                        "observation_count": len(observations),
                        "visit_count": len(unique_doc_ids),
                        "trends_count": len(trends),
                        "persistent_count": dynamics_report.summary_counts.get("persistent_count", 0),
                        "new_count": dynamics_report.summary_counts.get("new_count", 0),
                    },
                )
            )

        # Re-fetch with loaded relationships
        refetch_stmt = (
            select(LongitudinalAnalysis)
            .options(
                selectinload(LongitudinalAnalysis.trends),
                selectinload(LongitudinalAnalysis.sections),
                selectinload(LongitudinalAnalysis.notes),
            )
            .where(LongitudinalAnalysis.id == analysis_id)
        )
        refetch_res = await self.db.execute(refetch_stmt)
        return refetch_res.scalars().first()

    async def get_patient_longitudinal_analysis(
        self,
        patient_id: str,
        analysis_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[LongitudinalAnalysis]:
        """
        Retrieves a completed longitudinal analysis. If none exists, runs one on-demand.
        """
        stmt = (
            select(LongitudinalAnalysis)
            .options(
                selectinload(LongitudinalAnalysis.trends),
                selectinload(LongitudinalAnalysis.sections),
                selectinload(LongitudinalAnalysis.notes),
            )
            .where(LongitudinalAnalysis.patient_id == patient_id)
        )
        if analysis_id:
            stmt = stmt.where(LongitudinalAnalysis.id == analysis_id)
        else:
            stmt = stmt.order_by(desc(LongitudinalAnalysis.created_at)).limit(1)

        res = await self.db.execute(stmt)
        analysis = res.scalars().first()

        if not analysis and not analysis_id:
            # Generate on the fly
            analysis = await self.run_longitudinal_analysis(
                patient_id=patient_id,
                actor_id=actor_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        if analysis and self.audit_service:
            await self.audit_service.log_event(
                AuditLogCreate(
                    actor_id=actor_id,
                    action="LONGITUDINAL_SUMMARY_VIEWED",
                    resource_type="patients",
                    resource_id=patient_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "analysis_id": analysis.id,
                        "analysis_version": analysis.analysis_version,
                    },
                )
            )

        return analysis

    # ---------------------------------------------------------------------
    # Phase 4: Clinician Longitudinal Review Notes
    # ---------------------------------------------------------------------

    async def create_review_note(
        self,
        patient_id: str,
        note_data: LongitudinalReviewNoteCreate,
        author_id: str,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> LongitudinalReviewNote:
        note_id = str(uuid.uuid4())
        note = LongitudinalReviewNote(
            id=note_id,
            patient_id=patient_id,
            analysis_id=note_data.analysis_id,
            author_id=author_id,
            note=note_data.note,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)

        if self.audit_service:
            await self.audit_service.log_event(
                AuditLogCreate(
                    actor_id=actor_id or author_id,
                    action="LONGITUDINAL_REVIEW_NOTE_CREATED",
                    resource_type="patients",
                    resource_id=patient_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={
                        "note_id": note_id,
                        "analysis_id": note_data.analysis_id,
                        "author_id": author_id,
                    },
                )
            )

        return note

    async def list_review_notes(
        self,
        patient_id: str,
        analysis_id: Optional[str] = None,
    ) -> List[LongitudinalReviewNote]:
        stmt = select(LongitudinalReviewNote).where(LongitudinalReviewNote.patient_id == patient_id)
        if analysis_id:
            stmt = stmt.where(LongitudinalReviewNote.analysis_id == analysis_id)
        stmt = stmt.order_by(desc(LongitudinalReviewNote.created_at))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
