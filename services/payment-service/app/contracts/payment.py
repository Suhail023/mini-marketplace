"""Payment contracts."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.models.payment import Payment


class ChargeRequest(BaseModel):
    order_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    card_last_four: str | None = Field(None, max_length=4)


class PaymentResponse(BaseModel):
    id: str
    idempotency_key: str
    order_id: str
    amount: Decimal
    currency: str
    status: str
    card_last_four: str | None = None
    created_at: datetime | None = None

    @classmethod
    def from_payment_model(cls, payment: "Payment") -> "PaymentResponse":
        return cls(
            id=payment.id,
            idempotency_key=payment.idempotency_key,
            order_id=payment.order_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            card_last_four=payment.card_last_four,
            created_at=payment.created_at,
        )


class PaymentListResponse(BaseModel):
    payments: list[PaymentResponse]
    total: int
