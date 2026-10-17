"""Payment service with idempotency logic."""

import random

from app.contracts.payment import ChargeRequest, PaymentResponse
from app.repositories.payment_repository import PaymentRepository
from app.utils.errors import ConflictError, NotFoundError
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


class PaymentService:
    def __init__(self, payment_repository: PaymentRepository) -> None:
        self.payment_repository = payment_repository

    async def charge(self, request: ChargeRequest) -> PaymentResponse:
        existing = await self.payment_repository.get_by_idempotency_key(request.idempotency_key)
        if existing:
            logger.info("Replaying payment for idempotency key", extra={"payment_id": existing.id})
            return PaymentResponse.from_payment_model(existing)

        # Mock payment processing - 90% success rate (non-cryptographic, intentional mock)
        status = "succeeded" if random.random() < 0.9 else "failed"  # noqa: S311

        try:
            payment = await self.payment_repository.create(
                {
                    "idempotency_key": request.idempotency_key,
                    "order_id": request.order_id,
                    "amount": request.amount,
                    "currency": request.currency,
                    "status": status,
                    "card_last_four": request.card_last_four or "4242",
                }
            )
        except ConflictError:
            # A concurrent retry with the same key won the insert; replay its result.
            winner = await self.payment_repository.get_by_idempotency_key(request.idempotency_key)
            if winner is None:
                raise
            return PaymentResponse.from_payment_model(winner)

        logger.info("Payment created", extra={"payment_id": payment.id, "status": status})
        return PaymentResponse.from_payment_model(payment)

    async def get_payment(self, payment_id: str) -> PaymentResponse:
        payment = await self.payment_repository.get_by_id(payment_id)
        if payment is None:
            raise NotFoundError("Payment", payment_id)
        return PaymentResponse.from_payment_model(payment)
