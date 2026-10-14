"""Notification contracts."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.notification import Notification


class NotificationResponse(BaseModel):
    id: str
    event_id: str
    order_id: str
    user_id: str
    type: str
    title: str
    message: str
    status: str
    created_at: datetime | None = None
    sent_at: datetime | None = None

    @classmethod
    def from_notification_model(cls, notification: "Notification") -> "NotificationResponse":
        return cls(
            id=notification.id,
            event_id=notification.event_id,
            order_id=notification.order_id,
            user_id=notification.user_id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            status=notification.status,
            created_at=notification.created_at,
            sent_at=notification.sent_at,
        )


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
