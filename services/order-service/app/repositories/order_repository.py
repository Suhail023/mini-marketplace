"""Order repository."""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.outbox import OutboxEvent
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, order_data: dict) -> Order:
        order = Order(**order_data)
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_by_id(self, order_id: str) -> Order | None:
        return await self.db.get(Order, order_id)

    async def get_by_idempotency_key(self, idempotency_key: str) -> Order | None:
        result = await self.db.execute(
            select(Order).where(Order.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self, order_id: str, status: str, payment_id: str | None = None
    ) -> Order | None:
        order = await self.db.get(Order, order_id)
        if not order:
            return None
        order.status = status
        if payment_id:
            order.payment_id = payment_id
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def update_status_with_outbox(
        self,
        order_id: str,
        status: str,
        payment_id: str | None,
        event_payload: dict,
        routing_key: str,
    ) -> Order:
        """Update order status and write an outbox event in the same transaction.

        This is the core of the outbox pattern: the order status change and the
        event write are atomic — either both succeed or both fail. A separate
        background publisher polls the outbox table and pushes to RabbitMQ.
        """
        order = await self.db.get(Order, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        order.status = status
        if payment_id:
            order.payment_id = payment_id

        outbox_event = OutboxEvent(
            aggregate_type="order",
            aggregate_id=order_id,
            event_type="OrderCreated",
            payload=json.dumps(event_payload, default=str),
            routing_key=routing_key,
            status="pending",
        )
        self.db.add(outbox_event)

        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def list_by_user(self, user_id: str, skip: int = 0, limit: int = 20) -> list[Order]:
        result = await self.db.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
