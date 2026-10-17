"""Payment repository with idempotency support."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.utils.errors import ConflictError


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def create(self, fields: dict[str, Any]) -> Payment:
        payment = Payment(**fields)
        self.session.add(payment)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("Idempotency key is already in use", "idempotency_key")
        await self.session.refresh(payment)
        return payment

    async def get_by_id(self, payment_id: str) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def get_by_order_id(self, order_id: str) -> list[Payment]:
        result = await self.session.execute(select(Payment).where(Payment.order_id == order_id))
        return list(result.scalars().all())
