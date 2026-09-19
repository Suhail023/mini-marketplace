"""Order domain events."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderCreatedEvent(BaseModel):
    """Emitted when an order is confirmed or failed.

    Published via RabbitMQ after the order status is written to the DB
    in the same transaction (outbox pattern).
    """

    event_id: str = Field(..., description="Unique event ID (UUID)")
    order_id: str = Field(..., description="Order ID")
    user_id: str = Field(..., description="User who placed the order")
    product_id: str = Field(..., description="Product ordered")
    quantity: int = Field(..., ge=1)
    total_amount: Decimal = Field(..., description="Total charged")
    status: str = Field(..., description="Order final status: confirmed or failed")
    payment_id: str | None = Field(None, description="Payment ID if confirmed")
    idempotency_key: str = Field(..., description="Original idempotency key")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
