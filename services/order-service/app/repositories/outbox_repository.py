"""Outbox repository — data access for the transactional outbox table."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent

UNPUBLISHED_STATUSES = ("pending", "failed")


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_unpublished(self, limit: int = 50) -> list[OutboxEvent]:
        result = await self.session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status.in_(UNPUBLISHED_STATUSES))
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_published(self, event_id: str) -> None:
        await self.session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(status="published", published_at=datetime.now(UTC))
        )
        await self.session.commit()

    async def mark_failed(self, event_id: str) -> None:
        await self.session.execute(
            update(OutboxEvent).where(OutboxEvent.id == event_id).values(status="failed")
        )
        await self.session.commit()
