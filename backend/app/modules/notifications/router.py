from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user_token
from app.modules.notifications.schemas import NotificationCreate, NotificationResponse
from app.modules.notifications.service import NotificationService

router = APIRouter()


@router.get("/me", response_model=List[NotificationResponse])
async def get_my_notifications(
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(get_current_user_token),
):
    service = NotificationService(db)
    user_id = token.get("sub", "00000000-0000-0000-0000-000000000001")
    return await service.list_for_user(user_id=user_id, unread_only=unread_only)


@router.post("/{notif_id}/read", status_code=status.HTTP_200_OK)
async def mark_notification_read(
    notif_id: str,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(get_current_user_token),
):
    service = NotificationService(db)
    success = await service.mark_as_read(notif_id)
    return {"success": success}
