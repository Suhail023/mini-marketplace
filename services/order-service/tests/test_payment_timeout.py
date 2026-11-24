from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import httpx

from app.clients import CircuitBreaker, PaymentClient, PaymentOutcomeUnknownError
from app.contracts.order import CreateOrderRequest
from app.models.order import Order
from app.services.order_service import OrderService


class PaymentTimeoutTest(IsolatedAsyncioTestCase):
    async def check_recovery(self, payment_status, expected_status):
        request = CreateOrderRequest(product_id="product", quantity=1, idempotency_key="checkout")
        order = Order(
            id="order",
            user_id="user",
            product_id="product",
            quantity=1,
            idempotency_key="checkout",
            total_amount=Decimal("10"),
            status="pending",
        )
        repository = AsyncMock()
        repository.get_by_idempotency_key.side_effect = [None, order]
        repository.create.return_value = order
        repository.lock_for_recovery.return_value = order
        product = AsyncMock()
        product.get_product.return_value.price = order.total_amount
        payment = PaymentClient("http://payment", 1, CircuitBreaker())
        service = OrderService(repository, product, payment)
        outcomes = [httpx.ReadTimeout("lost reply"), {"id": "payment", "status": payment_status}]
        with patch.object(payment, "_post_charge", new=AsyncMock(side_effect=outcomes)) as charge:
            with self.assertRaises(PaymentOutcomeUnknownError):
                await service.create_order(request, "user")
            self.assertEqual(order.status, "payment_unknown")
            repository.finalize_with_outbox.assert_not_awaited()
            product.release_stock.assert_not_awaited()
            repository.finalize_with_outbox.return_value = order
            await service.create_order(request, "user")
            self.assertEqual(charge.await_args_list[0], charge.await_args_list[1])
        self.assertEqual(repository.finalize_with_outbox.await_args.args[1], expected_status)
        product.reserve_stock.assert_awaited_once()
        self.assertEqual(product.release_stock.await_count, int(payment_status == "failed"))

    async def test_charge_succeeded_before_timeout(self):
        await self.check_recovery("succeeded", "confirmed")

    async def test_decline_after_timeout(self):
        await self.check_recovery("failed", "failed")
