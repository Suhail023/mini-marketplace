"""Order contracts."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.models.order import Order


class CreateOrderRequest(BaseModel):
    # The ordering user is taken from the JWT `sub` claim, never from the body.
    product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    card_last_four: str | None = Field(None, max_length=4)


class OrderResponse(BaseModel):
    id: str
    user_id: str
    product_id: str
    quantity: int
    total_amount: Decimal
    status: str
    payment_id: str | None = None
    idempotency_key: str
    created_at: datetime | None = None

    @classmethod
    def from_order_model(cls, order: "Order") -> "OrderResponse":
        return cls(
            id=order.id,
            user_id=order.user_id,
            product_id=order.product_id,
            quantity=order.quantity,
            total_amount=order.total_amount,
            status=order.status,
            payment_id=order.payment_id,
            idempotency_key=order.idempotency_key,
            created_at=order.created_at,
        )


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
