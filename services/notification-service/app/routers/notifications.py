"""Notification routes. Users can only read their own notifications (JWT subject)."""

from fastapi import APIRouter, Depends, Query

from app.contracts.notification import NotificationListResponse, NotificationResponse
from app.dependencies import get_notification_service
from app.services.notification_service import NotificationService
from common.auth import Principal, get_current_principal

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
async def list_my_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    return await service.list_notifications(principal.user_id, skip=skip, limit=limit)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    principal: Principal = Depends(get_current_principal),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    return await service.get_notification(notification_id, user_id=principal.user_id)
