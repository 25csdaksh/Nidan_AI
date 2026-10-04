from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationCreate


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: str, unread_only: bool = False) -> List[Notification]:
        stmt = select(Notification).where(Notification.recipient_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)
        stmt = stmt.order_by(Notification.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_notification(self, data: NotificationCreate) -> Notification:
        notif = Notification(
            recipient_id=data.recipient_id,
            title=data.title,
            message=data.message,
            severity=data.severity,
            link=data.link,
        )
        self.db.add(notif)
        await self.db.flush()
        await self.db.refresh(notif)
        return notif

    async def mark_as_read(self, notif_id: str) -> bool:
        result = await self.db.execute(select(Notification).where(Notification.id == notif_id))
        notif = result.scalar_one_or_none()
        if notif:
            notif.is_read = True
            await self.db.flush()
            return True
        return False
