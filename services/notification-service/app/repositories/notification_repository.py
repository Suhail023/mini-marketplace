"""Notification repository."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.utils.errors import ConflictError


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, fields: dict[str, Any]) -> Notification:
        notification = Notification(**fields)
        self.session.add(notification)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("Event was already processed", "event_id")
        await self.session.refresh(notification)
        return notification

    async def get_by_id(self, notification_id: str) -> Notification | None:
        return await self.session.get(Notification, notification_id)

    async def get_by_event_id(self, event_id: str) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(Notification.event_id == event_id)
        )
        return result.scalar_one_or_none()

    async def list_page_by_user(
        self, user_id: str, skip: int, limit: int
    ) -> tuple[list[Notification], int]:
        condition = Notification.user_id == user_id
        total = await self.session.scalar(
            select(func.count()).select_from(Notification).where(condition)
        )
        result = await self.session.execute(
            select(Notification)
            .where(condition)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total or 0
