"""Notification repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, notification_data: dict) -> Notification:
        notification = Notification(**notification_data)
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def get_by_id(self, notification_id: str) -> Notification | None:
        return await self.db.get(Notification, notification_id)

    async def get_by_event_id(self, event_id: str) -> Notification | None:
        result = await self.db.execute(
            select(Notification).where(Notification.event_id == event_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
