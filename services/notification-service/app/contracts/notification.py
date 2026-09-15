"""Notification contracts."""

from datetime import datetime

from pydantic import BaseModel


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


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
