import asyncio
from collections import Counter
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.models.outbox import (
    RELEASE_PENDING,
    STOCK_RELEASE_EVENT,
    Base,
    OutboxEvent,
    StockReleaseRetry,
)
from app.publisher import OutboxPublisher


class StockReleaseSchedulingTest(IsolatedAsyncioTestCase):
    async def test_release_51_completes_while_first_50_keep_failing(self):
        engine = create_async_engine("sqlite+aiosqlite://")
        self.addAsyncCleanup(engine.dispose)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        start = datetime.now(UTC) - timedelta(hours=1)
        async with sessions() as session:
            for number in range(1, 52):
                session.add(
                    OutboxEvent(
                        id=str(number),
                        aggregate_type="order",
                        aggregate_id=str(number),
                        event_type=STOCK_RELEASE_EVENT,
                        routing_key="stock.release",
                        payload='{"product_id":"item","quantity":1}',
                        status=RELEASE_PENDING,
                        created_at=start + timedelta(seconds=number),
                    )
                )
            await session.commit()

        attempts = Counter()

        async def deliver(product_id, quantity, order_id):
            attempts[order_id] += 1
            if order_id != "51":
                raise RuntimeError("Product deleted")

        client = AsyncMock()
        client.release_stock.side_effect = deliver
        with (
            patch("app.publisher.db.session", sessions),
            patch("app.publisher.get_product_client", return_value=client),
            patch("app.publisher.logger"),
        ):
            await OutboxPublisher().release_pending_stock()
            self.assertEqual(len(attempts), 50)
            self.assertNotIn("51", attempts)
            await OutboxPublisher().release_pending_stock()
            async with sessions() as session:
                self.assertEqual((await session.get(OutboxEvent, "51")).status, "published")
                self.assertTrue(all(count == 1 for count in attempts.values()))
                # Make the scheduled retries due without sleeping in the test.
                await session.execute(update(StockReleaseRetry).values(retry_at=start))
                await session.commit()
            await OutboxPublisher().release_pending_stock()
            self.assertEqual(attempts["51"], 1)
            self.assertTrue(all(attempts[str(i)] == 2 for i in range(1, 51)))

    async def test_events_publish_while_a_stock_release_is_blocked(self):
        directory = self.enterContext(TemporaryDirectory())
        db_path = Path(directory) / "outbox.db"
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            poolclass=AsyncAdaptedQueuePool,
            pool_size=1,
            max_overflow=0,
        )
        self.addAsyncCleanup(engine.dispose)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            session.add(
                OutboxEvent(
                    aggregate_type="order",
                    aggregate_id="declined-order",
                    event_type=STOCK_RELEASE_EVENT,
                    routing_key="stock.release",
                    payload='{"product_id":"item","quantity":1}',
                    status=RELEASE_PENDING,
                    created_at=datetime.now(UTC) - timedelta(seconds=1),
                )
            )
            await session.commit()

        release_started = asyncio.Event()
        finish_release = asyncio.Event()
        notification_sent = asyncio.Event()

        async def release_stock(*args):
            release_started.set()
            await finish_release.wait()

        async def publish_message(**kwargs):
            notification_sent.set()

        async def enqueue_notification():
            async with sessions() as session:
                session.add(
                    OutboxEvent(
                        id="notification",
                        aggregate_type="order",
                        aggregate_id="unrelated-order",
                        event_type="OrderCreated",
                        routing_key="order.created",
                        payload="{}",
                    )
                )
                await session.commit()

        client = AsyncMock()
        client.release_stock.side_effect = release_stock
        publisher = OutboxPublisher()
        exchange = object()
        with (
            patch("app.publisher.db.session", sessions),
            patch("app.publisher.get_product_client", return_value=client),
            patch("app.publisher.POLL_INTERVAL_SECONDS", 0.01),
            patch.object(publisher, "_get_exchange", new=AsyncMock(return_value=exchange)),
            patch("app.publisher.publish_message", side_effect=publish_message) as publish,
        ):
            task = asyncio.create_task(publisher.run())
            try:
                await asyncio.wait_for(release_started.wait(), timeout=2)
                await asyncio.wait_for(enqueue_notification(), timeout=2)
                await asyncio.wait_for(notification_sent.wait(), timeout=2)
                publish.assert_awaited_once_with(
                    exchange=exchange,
                    routing_key="order.created",
                    message={},
                    correlation_id="notification",
                )
            finally:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
