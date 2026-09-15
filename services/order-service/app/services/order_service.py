"""Order service - orchestrates Product and Payment services."""

import uuid

from app.clients import (
    charge_payment,
    check_and_reserve_stock,
    get_product,
    release_stock,
)
from app.contracts.order import CreateOrderRequest, OrderResponse
from app.repositories.order_repository import OrderRepository
from app.utils.logging import setup_logger
from shared.events.order import OrderCreatedEvent

logger = setup_logger(__name__)

ORDER_EVENTS_ROUTING_KEY = "order.created"


async def _rollback_stock(product_id: str, quantity: int, order_id: str) -> None:
    """Compensating action: restore stock that was decremented for a failed order."""
    try:
        await release_stock(product_id, quantity)
        logger.info(f"Stock rolled back for order {order_id}: +{quantity} units of {product_id}")
    except Exception as rollback_err:
        logger.error(
            f"STOCK ROLLBACK FAILED for order {order_id} "
            f"(product={product_id}, qty={quantity}): {rollback_err}. "
            "Manual inventory reconciliation required."
        )


def _extract_price(product_data: dict, product_id: str) -> float:
    """Extract price from product-service response.

    The product-service returns a flat dict: {"id": ..., "price": ..., ...}.
    Raises ValueError if the price field is missing or not positive.
    """
    if "price" in product_data:
        price = product_data["price"]
    elif "data" in product_data and "price" in product_data["data"]:
        price = product_data["data"]["price"]
    else:
        raise ValueError(
            f"Product service response for '{product_id}' is missing a 'price' field. "
            f"Got keys: {list(product_data.keys())}"
        )

    if not isinstance(price, int | float) or price <= 0:
        raise ValueError(
            f"Product '{product_id}' has an invalid price: {price!r}. Price must be > 0."
        )

    return float(price)


def _build_event_payload(order, status: str) -> dict:  # noqa: ANN001
    """Build the OrderCreated event payload from an order ORM object."""
    event = OrderCreatedEvent(
        event_id=str(uuid.uuid4()),
        order_id=order.id,
        user_id=order.user_id,
        product_id=order.product_id,
        quantity=order.quantity,
        total_amount=order.total_amount,
        status=status,
        payment_id=order.payment_id,
        idempotency_key=order.idempotency_key,
    )
    return event.model_dump(mode="json")


class OrderService:
    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository

    async def create_order(self, request: CreateOrderRequest) -> OrderResponse:
        existing = await self.order_repository.get_by_idempotency_key(request.idempotency_key)
        if existing:
            logger.info(f"Returning existing order for idempotency key: {request.idempotency_key}")
            return OrderResponse(
                id=existing.id,
                user_id=existing.user_id,
                product_id=existing.product_id,
                quantity=existing.quantity,
                total_amount=existing.total_amount,
                status=existing.status,
                payment_id=existing.payment_id,
                idempotency_key=existing.idempotency_key,
                created_at=existing.created_at,
            )

        # Step 1: Get product and calculate total — raises on missing/invalid price
        product_data = await get_product(request.product_id)
        price = _extract_price(product_data, request.product_id)
        total_amount = price * request.quantity

        # Step 2: Create pending order
        order_data = {
            "user_id": request.user_id,
            "product_id": request.product_id,
            "quantity": request.quantity,
            "total_amount": total_amount,
            "status": "pending",
            "idempotency_key": request.idempotency_key,
        }
        order = await self.order_repository.create(order_data)
        logger.info(f"Created pending order {order.id}")

        stock_reserved = False
        try:
            # Step 3: Reserve stock
            await check_and_reserve_stock(request.product_id, request.quantity)
            stock_reserved = True
            logger.info(f"Stock reserved for order {order.id}")

            # Step 4: Charge payment
            payment_result = await charge_payment(
                order_id=order.id,
                amount=total_amount,
                idempotency_key=f"payment-{request.idempotency_key}",
                card_last_four=request.card_last_four,
            )

            if payment_result.get("status") == "succeeded":
                order = await self.order_repository.update_status_with_outbox(
                    order.id,
                    "confirmed",
                    payment_result.get("id"),
                    _build_event_payload(order, "confirmed"),
                    ORDER_EVENTS_ROUTING_KEY,
                )
                logger.info(f"Order {order.id} confirmed with payment {payment_result.get('id')}")
            else:
                logger.warning(
                    f"Order {order.id} failed: payment status={payment_result.get('status')}. "
                    "Rolling back reserved stock."
                )
                await _rollback_stock(request.product_id, request.quantity, order.id)
                order = await self.order_repository.update_status_with_outbox(
                    order.id,
                    "failed",
                    None,
                    _build_event_payload(order, "failed"),
                    ORDER_EVENTS_ROUTING_KEY,
                )

        except Exception as e:
            logger.error(f"Order {order.id} failed with exception: {e}")
            if stock_reserved:
                await _rollback_stock(request.product_id, request.quantity, order.id)
            order = await self.order_repository.update_status_with_outbox(
                order.id,
                "failed",
                None,
                _build_event_payload(order, "failed"),
                ORDER_EVENTS_ROUTING_KEY,
            )
            raise

        return OrderResponse(
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

    async def get_order(self, order_id: str) -> OrderResponse | None:
        order = await self.order_repository.get_by_id(order_id)
        if not order:
            return None
        return OrderResponse(
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

    async def list_orders(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> list[OrderResponse]:
        orders = await self.order_repository.list_by_user(user_id, skip=skip, limit=limit)
        return [
            OrderResponse(
                id=o.id,
                user_id=o.user_id,
                product_id=o.product_id,
                quantity=o.quantity,
                total_amount=o.total_amount,
                status=o.status,
                payment_id=o.payment_id,
                idempotency_key=o.idempotency_key,
                created_at=o.created_at,
            )
            for o in orders
        ]
