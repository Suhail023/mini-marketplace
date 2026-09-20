"""Outbox repository — data access for the transactional outbox table."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxEvent
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


class OutboxRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, event_data: dict) -> OutboxEvent:
        """Insert an outbox event (called within an existing transaction)."""
        event = OutboxEvent(**event_data)
        self.db.add(event)
        return event

    async def get_pending(self, limit: int = 50) -> list[OutboxEvent]:
        """Fetch unprocessed events for the publisher to pick up."""
        result = await self.db.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status == "pending")
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_published(self, event_id: str) -> None:
        """Mark an event as successfully published."""
        await self.db.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(status="published", published_at=datetime.now(UTC))
        )
        await self.db.commit()

    async def mark_failed(self, event_id: str) -> None:
        """Mark an event as failed (will be retried on next poll)."""
        await self.db.execute(
            update(OutboxEvent).where(OutboxEvent.id == event_id).values(status="failed")
        )
        await self.db.commit()
