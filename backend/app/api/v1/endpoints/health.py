from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.queue import get_task_broker
from app.core.storage import get_storage_service

router = APIRouter()


@router.get("/health", summary="System Health & Readiness Probe")
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    # 1. Database Check
    db_status = "unhealthy"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # 2. Broker Check
    broker = get_task_broker()
    broker_ok = await broker.is_healthy()
    broker_status = "healthy" if broker_ok else "degraded"

    # 3. Storage Check
    storage = get_storage_service()
    storage_ok = await storage.is_healthy()
    storage_status = "healthy" if storage_ok else "unhealthy"

    overall_healthy = db_status == "healthy" and storage_ok

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.PROJECT_NAME,
        "tagline": settings.PROJECT_TAGLINE,
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0-phase0",
        "cdss_disclaimer": settings.CDSS_DISCLAIMER,
        "components": {
            "database": db_status,
            "broker": broker_status,
            "storage": {
                "status": storage_status,
                "backend": settings.STORAGE_BACKEND,
            },
        },
        "modules": [
            "auth",
            "users",
            "patients",
            "medical_records",
            "reports",
            "lab",
            "prescriptions",
            "imaging",
            "ai",
            "audit",
            "notifications",
        ],
    }
