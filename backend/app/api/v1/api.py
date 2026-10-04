from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.modules.ai import router as ai_router
from app.modules.audit import router as audit_router
from app.modules.auth import router as auth_router
from app.modules.imaging import router as imaging_router
from app.modules.lab import router as lab_router
from app.modules.medical_documents import router as medical_documents_router
from app.modules.medical_records import router as medical_records_router
from app.modules.notifications import router as notifications_router
from app.modules.patients import router as patients_router
from app.modules.prescriptions import router as prescriptions_router
from app.modules.reports import router as reports_router
from app.modules.users import router as users_router

from app.modules.clinical_intelligence import clinical_intelligence_router
from app.modules.prescription_intelligence import prescription_intelligence_router

api_v1_router = APIRouter()

# Core Probes
api_v1_router.include_router(health.router, tags=["Health & System Probes"])

# Modular Domain Routers
api_v1_router.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(users_router.router, prefix="/users", tags=["Users & Clinicians"])
api_v1_router.include_router(patients_router.router, prefix="/patients", tags=["Patients"])
api_v1_router.include_router(
    medical_documents_router.router,
    prefix="/medical-documents",
    tags=["Medical Documents & Secure Ingestion (Phase 1)"],
)
api_v1_router.include_router(
    clinical_intelligence_router,
    tags=["Clinical Intelligence & Anomaly Engine (Phase 3 & 4)"],
)
api_v1_router.include_router(
    prescription_intelligence_router,
    tags=["Prescription Intelligence & Medication Safety (Phase 5)"],
)
api_v1_router.include_router(
    medical_records_router.router,
    prefix="/medical-records",
    tags=["Medical Records & Encounters"],
)
api_v1_router.include_router(reports_router.router, prefix="/reports", tags=["Reports & Ingestion"])
api_v1_router.include_router(lab_router.router, prefix="/lab", tags=["Laboratory & Analytes"])
api_v1_router.include_router(
    prescriptions_router.router,
    prefix="/prescriptions",
    tags=["Prescriptions & Medications"],
)
api_v1_router.include_router(
    imaging_router.router,
    prefix="/imaging",
    tags=["Imaging Studies (X-Ray & USG)"],
)
api_v1_router.include_router(ai_router.router, prefix="/ai", tags=["AI Clinical Pipeline (Phase 0 Scaffold)"])
api_v1_router.include_router(audit_router.router, prefix="/audit", tags=["HIPAA Audit Trail"])
api_v1_router.include_router(
    notifications_router.router,
    prefix="/notifications",
    tags=["Clinical Alerts & Notifications"],
)
