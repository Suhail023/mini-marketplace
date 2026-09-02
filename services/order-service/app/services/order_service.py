"""Order service - orchestrates Product and Payment services."""

import uuid

from app.clients import charge_payment, check_and_reserve_stock, get_product
from app.contracts.order import CreateOrderRequest, OrderResponse
from app.repositories.order_repository import OrderRepository
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


class OrderService:
    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository

    async def create_order(self, request: CreateOrderRequest) -> OrderResponse:
        existing = await self.order_repository.get_by_idempotency_key(
            request.idempotency_key
        )
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

        # Step 1: Get product to calculate total
        product_data = await get_product(request.product_id)
        product = product_data.get("error", {}).get("data") or product_data
        # product-service returns { error: { data: {...} } } or flat
        if "error" in product_data and product_data["error"]:
            raise Exception(f"Product not found: {request.product_id}")

        # Extract price from the response - product-service wraps in {error: {data: ...}}
        if "data" in product_data:
            price = product_data["data"]["price"]
            product_name = product_data["data"]["name"]
        elif "price" in product_data:
            price = product_data["price"]
            product_name = product_data["name"]
        else:
            # Try the nested error.data pattern (product-service contract format)
            price = product.get("price", 0)
            product_name = product.get("name", "unknown")

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

        try:
            # Step 3: Reserve stock
            await check_and_reserve_stock(request.product_id, request.quantity)
            logger.info(f"Stock reserved for order {order.id}")

            # Step 4: Charge payment
            payment_result = await charge_payment(
                order_id=order.id,
                amount=total_amount,
                idempotency_key=f"payment-{request.idempotency_key}",
                card_last_four=request.card_last_four,
            )

            if payment_result.get("status") == "succeeded":
                order = await self.order_repository.update_status(
                    order.id, "confirmed", payment_result.get("id")
                )
                logger.info(f"Order {order.id} confirmed with payment {payment_result.get('id')}")
            else:
                order = await self.order_repository.update_status(order.id, "failed")
                logger.warning(f"Order {order.id} failed: payment not successful")

        except Exception as e:
            logger.error(f"Order {order.id} failed: {e}")
            order = await self.order_repository.update_status(order.id, "failed")
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

    async def list_orders(self, user_id: str, skip: int = 0, limit: int = 20) -> list[OrderResponse]:
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
