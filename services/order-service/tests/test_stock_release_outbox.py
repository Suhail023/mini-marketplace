from decimal import Decimal
from unittest import IsolatedAsyncioTestCase

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.order import Base, Order
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository


class DeclinedOrderTest(IsolatedAsyncioTestCase):
    async def test_release_survives_checkout_session(self):
        engine = create_async_engine("sqlite+aiosqlite://")
        self.addAsyncCleanup(engine.dispose)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            order = Order(
                id="order",
                user_id="user",
                product_id="item",
                quantity=2,
                total_amount=Decimal("2"),
                idempotency_key="key",
                status="payment_unknown",
            )
            session.add(order)
            await session.commit()
            await OrderRepository(session).finalize_with_outbox(
                order, "failed", None, "OrderCreated", {}, "order.created", release_stock=True
            )
        async with sessions() as session:
            self.assertEqual((await session.get(Order, "order")).status, "failed")
            outbox = OutboxRepository(session)
            (release,) = await outbox.get_pending_releases()
            self.assertEqual(release.aggregate_id, "order")
            (event,) = await outbox.get_unpublished()
            self.assertEqual(event.event_type, "OrderCreated")
            await outbox.mark_published(release.id)
            self.assertEqual(await outbox.get_pending_releases(), [])
