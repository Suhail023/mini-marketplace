"""Notification routes. Users can only read their own notifications (JWT subject)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.notification import NotificationListResponse, NotificationResponse
from app.database import get_db
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService
from common.auth import Principal, get_current_principal

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    repo = NotificationRepository(db)
    return NotificationService(repo)


@router.get("/", response_model=NotificationListResponse)
async def list_my_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
    service: NotificationService = Depends(_get_notification_service),
):
    notifications = await service.list_notifications(principal.user_id, skip=skip, limit=limit)
    return NotificationListResponse(notifications=notifications, total=len(notifications))


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    principal: Principal = Depends(get_current_principal),
    service: NotificationService = Depends(_get_notification_service),
):
    notification = await service.get_notification(notification_id)
    # 404 (not 403) for other users' notifications so IDs can't be probed.
    if not notification or notification.user_id != principal.user_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification
