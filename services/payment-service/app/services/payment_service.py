"""Payment service with idempotency logic."""

import random

from app.contracts.payment import ChargeRequest, PaymentResponse
from app.repositories.payment_repository import PaymentRepository
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


class PaymentService:
    def __init__(self, payment_repository: PaymentRepository):
        self.payment_repository = payment_repository

    async def charge(self, request: ChargeRequest) -> PaymentResponse:
        existing = await self.payment_repository.get_by_idempotency_key(request.idempotency_key)
        if existing:
            logger.info(
                f"Returning existing payment for idempotency key: {request.idempotency_key}"
            )
            return PaymentResponse(
                id=existing.id,
                idempotency_key=existing.idempotency_key,
                order_id=existing.order_id,
                amount=existing.amount,
                currency=existing.currency,
                status=existing.status,
                card_last_four=existing.card_last_four,
                created_at=existing.created_at,
            )

        # Mock payment processing - 90% success rate (non-cryptographic, intentional mock)
        status = "succeeded" if random.random() < 0.9 else "failed"  # noqa: S311

        payment_data = {
            "idempotency_key": request.idempotency_key,
            "order_id": request.order_id,
            "amount": request.amount,
            "currency": request.currency,
            "status": status,
            "card_last_four": request.card_last_four or "4242",
        }

        payment = await self.payment_repository.create(payment_data)
        logger.info(f"Payment {payment.id} created with status: {status}")

        return PaymentResponse(
            id=payment.id,
            idempotency_key=payment.idempotency_key,
            order_id=payment.order_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            card_last_four=payment.card_last_four,
            created_at=payment.created_at,
        )

    async def get_payment(self, payment_id: str) -> PaymentResponse | None:
        payment = await self.payment_repository.get_by_id(payment_id)
        if not payment:
            return None
        return PaymentResponse(
            id=payment.id,
            idempotency_key=payment.idempotency_key,
            order_id=payment.order_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            card_last_four=payment.card_last_four,
            created_at=payment.created_at,
        )
