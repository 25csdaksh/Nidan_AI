from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogCreate


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(self, data: AuditLogCreate) -> AuditLog:
        log_entry = AuditLog(
            actor_id=data.actor_id,
            action=data.action,
            resource_type=data.resource_type,
            resource_id=data.resource_id,
            ip_address=data.ip_address,
            user_agent=data.user_agent,
            details=data.details,
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    async def list_logs(
        self,
        resource_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        stmt = select(AuditLog)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
