"""Outbox repository — data access for the transactional outbox table."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import RELEASE_PENDING, OutboxEvent, StockReleaseRetry

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

    async def get_pending_releases(self, limit: int = 50) -> list[OutboxEvent]:
        due_at = func.coalesce(StockReleaseRetry.retry_at, OutboxEvent.created_at)
        result = await self.session.scalars(
            select(OutboxEvent)
            .outerjoin(StockReleaseRetry, StockReleaseRetry.event_id == OutboxEvent.id)
            .where(OutboxEvent.status == RELEASE_PENDING, due_at <= datetime.now(UTC))
            .order_by(due_at, OutboxEvent.id)
            .limit(limit)
        )
        return list(result)

    async def defer_release(self, event_id: str) -> None:
        retry_at = datetime.now(UTC) + timedelta(minutes=1)
        await self.session.execute(
            insert(StockReleaseRetry)
            .values(event_id=event_id, retry_at=retry_at)
            .on_conflict_do_update(
                index_elements=[StockReleaseRetry.event_id], set_={"retry_at": retry_at}
            )
        )
        await self.session.commit()

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
