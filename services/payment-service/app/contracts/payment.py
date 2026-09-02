"""Payment contracts."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChargeRequest(BaseModel):
    order_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    card_last_four: str | None = Field(None, max_length=4)


class PaymentResponse(BaseModel):
    id: str
    idempotency_key: str
    order_id: str
    amount: float
    currency: str
    status: str
    card_last_four: str | None = None
    created_at: datetime | None = None


class PaymentListResponse(BaseModel):
    payments: list[PaymentResponse]
    total: int
