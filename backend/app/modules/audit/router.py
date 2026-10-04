from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import UserRole, get_current_user_token, require_roles
from app.modules.audit.schemas import AuditLogResponse
from app.modules.audit.service import AuditService

router = APIRouter()


@router.get("/", response_model=List[AuditLogResponse])
async def list_audit_trail(
    resource_type: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.CHIEF_MEDICAL_OFFICER, UserRole.AUDITOR])),
):
    """Retrieve HIPAA-compliant immutable audit logs."""
    service = AuditService(db)
    return await service.list_logs(resource_type=resource_type, actor_id=actor_id, limit=limit)
