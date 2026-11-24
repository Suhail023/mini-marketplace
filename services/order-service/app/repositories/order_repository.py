"""Order repository."""

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderPaymentInput
from app.models.outbox import RELEASE_PENDING, STOCK_RELEASE_EVENT, OutboxEvent
from app.utils.errors import ConflictError


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def end_transaction(self) -> None:
        """Close the current transaction so its pooled connection is released.

        Call before slow remote work; otherwise the connection sits idle in
        transaction. expire_on_commit=False keeps loaded objects usable.
        """
        await self.session.commit()

    async def create(self, fields: dict[str, Any], *, card_last_four: str | None) -> Order:
        order = Order(**fields)
        self.session.add(order)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("Idempotency key is already in use", "idempotency_key")
        self.session.add(OrderPaymentInput(order_id=order.id, card_last_four=card_last_four))
        # Refresh before commit so no transaction is left open for the saga's remote calls.
        await self.session.refresh(order)
        await self.session.commit()
        return order

    async def get_payment_card_last_four(self, order_id: str) -> str | None:
        # Orders created before payment inputs were persisted use the payment service default.
        payment_input = await self.session.get(OrderPaymentInput, order_id)
        return payment_input.card_last_four if payment_input else None

    async def lock_for_recovery(self, order_id: str) -> Order:
        result = await self.session.execute(
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()

    async def get_by_id(self, order_id: str) -> Order | None:
        return await self.session.get(Order, order_id)

    async def get_by_idempotency_key(self, user_id: str, idempotency_key: str) -> Order | None:
        result = await self.session.execute(
            select(Order).where(Order.user_id == user_id, Order.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def finalize_with_outbox(
        self,
        order: Order,
        status: str,
        payment_id: str | None,
        event_type: str,
        event_payload: dict[str, Any],
        routing_key: str,
        *,
        release_stock: bool = False,
    ) -> Order:
        """Set the final order status and enqueue its event in one transaction.

        This is the core of the outbox pattern: the status change and the event
        row commit atomically; the background publisher ships the event later.
        """
        order.status = status
        if release_stock:
            self.session.add(
                OutboxEvent(
                    aggregate_type="order",
                    aggregate_id=order.id,
                    event_type=STOCK_RELEASE_EVENT,
                    routing_key="stock.release",
                    status=RELEASE_PENDING,
                    payload=json.dumps(
                        {"product_id": order.product_id, "quantity": order.quantity}
                    ),
                )
            )
        if payment_id:
            order.payment_id = payment_id

        self.session.add(
            OutboxEvent(
                aggregate_type="order",
                aggregate_id=order.id,
                event_type=event_type,
                payload=json.dumps(event_payload, default=str),
                routing_key=routing_key,
                status="pending",
            )
        )
        await self.session.flush()
        await self.session.refresh(order)
        await self.session.commit()
        return order

    async def list_page_by_user(
        self, user_id: str, skip: int, limit: int
    ) -> tuple[list[Order], int]:
        condition = Order.user_id == user_id
        total = await self.session.scalar(select(func.count()).select_from(Order).where(condition))
        result = await self.session.execute(
            select(Order)
            .where(condition)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total or 0
