"""Notification routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.notification import NotificationListResponse, NotificationResponse
from app.database import get_db
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    repo = NotificationRepository(db)
    return NotificationService(repo)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    service: NotificationService = Depends(_get_notification_service),
):
    notification = await service.get_notification(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.get("/user/{user_id}", response_model=NotificationListResponse)
async def list_notifications(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    service: NotificationService = Depends(_get_notification_service),
):
    notifications = await service.list_notifications(user_id, skip=skip, limit=limit)
    return NotificationListResponse(notifications=notifications, total=len(notifications))
