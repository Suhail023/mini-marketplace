from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.clients import CircuitBreaker, PaymentClient, PaymentOutcomeUnknownError
from app.contracts.order import CreateOrderRequest
from app.models import Base
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository
from app.services.order_service import OrderService


class PaymentTimeoutTest(IsolatedAsyncioTestCase):
    async def check_recovery(self, payment_status, expected_status, retry_card=None, error=None):
        engine = create_async_engine("sqlite+aiosqlite://")
        self.addAsyncCleanup(engine.dispose)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        request = CreateOrderRequest(
            product_id="product",
            quantity=1,
            idempotency_key="checkout",
            card_last_four="0123",
        )
        retry = CreateOrderRequest(
            product_id="another-product", quantity=2, idempotency_key="checkout"
        )
        if retry_card is not None:
            retry.card_last_four = retry_card
        product = AsyncMock()
        product.get_product.return_value.price = Decimal("10")
        payment = PaymentClient("http://payment", 1, CircuitBreaker())
        outcomes = [
            error or httpx.ReadTimeout("lost reply"),
            {"id": "payment", "status": payment_status},
        ]
        with patch.object(payment, "_post_charge", new=AsyncMock(side_effect=outcomes)) as charge:
            async with sessions() as session:
                service = OrderService(OrderRepository(session), product, payment)
                with self.assertRaises(PaymentOutcomeUnknownError):
                    await service.create_order(request, "user")
            async with sessions() as session:
                repository = OrderRepository(session)
                order = await repository.get_by_idempotency_key("user", "checkout")
                self.assertEqual(order.status, "payment_unknown")
                outbox = OutboxRepository(session)
                self.assertEqual(await outbox.get_unpublished(), [])
                self.assertEqual(await outbox.get_pending_releases(), [])
                result = await OrderService(repository, product, payment).create_order(
                    retry, "user"
                )
                self.assertEqual(result.status, expected_status)
                self.assertEqual(len(await outbox.get_unpublished()), 1)
                self.assertEqual(
                    len(await outbox.get_pending_releases()), int(payment_status == "failed")
                )
            self.assertEqual(charge.await_args_list[0].args[0]["card_last_four"], "0123")
            self.assertEqual(charge.await_args_list[0], charge.await_args_list[1])
        product.reserve_stock.assert_awaited_once()
        product.release_stock.assert_not_awaited()
        product.get_product.assert_awaited_once()

    async def test_charge_succeeded_before_timeout(self):
        await self.check_recovery("succeeded", "confirmed")

    async def test_decline_after_timeout(self):
        await self.check_recovery("failed", "failed", retry_card="9876")

    async def test_corrupt_gzip_after_successful_charge(self):
        with self.assertRaises(httpx.DecodingError) as failure:
            httpx.Response(200, headers={"Content-Encoding": "gzip"}, content=b"bad gzip")
        await self.check_recovery("succeeded", "confirmed", error=failure.exception)
