"""Payment repository with idempotency support."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def create(self, payment_data: dict) -> Payment:
        payment = Payment(**payment_data)
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def get_by_id(self, payment_id: str) -> Payment | None:
        return await self.db.get(Payment, payment_id)

    async def get_by_order_id(self, order_id: str) -> list[Payment]:
        result = await self.db.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        return list(result.scalars().all())
