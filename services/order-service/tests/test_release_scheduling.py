from collections import Counter
from datetime import UTC, datetime, timedelta
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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
            await OutboxPublisher().publish_unpublished()
            self.assertEqual(len(attempts), 50)
            self.assertNotIn("51", attempts)
            await OutboxPublisher().publish_unpublished()
            async with sessions() as session:
                self.assertEqual((await session.get(OutboxEvent, "51")).status, "published")
                self.assertTrue(all(count == 1 for count in attempts.values()))
                # Make the scheduled retries due without sleeping in the test.
                await session.execute(update(StockReleaseRetry).values(retry_at=start))
                await session.commit()
            await OutboxPublisher().publish_unpublished()
            self.assertEqual(attempts["51"], 1)
            self.assertTrue(all(attempts[str(i)] == 2 for i in range(1, 51)))
