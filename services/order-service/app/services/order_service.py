"""Order service - orchestrates the Product and Payment services as a saga."""

from typing import Any
import uuid

from app.clients import PaymentClient, PaymentOutcomeUnknownError, PaymentResult, ProductClient
from app.contracts.order import CreateOrderRequest, OrderListResponse, OrderResponse
from app.models.order import Order
from app.repositories.order_repository import OrderRepository
from app.utils.errors import ConflictError, NotFoundError
from app.utils.logging import setup_logger
from shared.events.order import OrderCreatedEvent

logger = setup_logger(__name__)

ORDER_EVENT_TYPE = "OrderCreated"
ORDER_EVENTS_ROUTING_KEY = "order.created"

STATUS_PAYMENT_UNKNOWN = "payment_unknown"
STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_FAILED = "failed"


def _build_event_payload(order: Order, status: str, payment_id: str | None) -> dict[str, Any]:
    event = OrderCreatedEvent(
        event_id=str(uuid.uuid4()),
        order_id=order.id,
        user_id=order.user_id,
        product_id=order.product_id,
        quantity=order.quantity,
        total_amount=order.total_amount,
        status=status,
        payment_id=payment_id,
        idempotency_key=order.idempotency_key,
    )
    return event.model_dump(mode="json")


class OrderService:
    def __init__(
        self,
        order_repository: OrderRepository,
        product_client: ProductClient,
        payment_client: PaymentClient,
    ) -> None:
        self.order_repository = order_repository
        self.product_client = product_client
        self.payment_client = payment_client

    async def create_order(self, request: CreateOrderRequest, user_id: str) -> OrderResponse:
        existing = await self.order_repository.get_by_idempotency_key(
            user_id, request.idempotency_key
        )
        if existing and existing.status == STATUS_PAYMENT_UNKNOWN:
            return await self._recover_payment(existing)
        if existing:
            logger.info("Replaying order for idempotency key", extra={"order_id": existing.id})
            return OrderResponse.from_order_model(existing)
        # Don't hold a pooled connection idle in transaction across the remote call.
        await self.order_repository.end_transaction()

        product = await self.product_client.get_product(request.product_id)

        try:
            order = await self.order_repository.create(
                {
                    "user_id": user_id,
                    "product_id": request.product_id,
                    "quantity": request.quantity,
                    "total_amount": product.price * request.quantity,
                    "status": STATUS_PENDING,
                    "idempotency_key": request.idempotency_key,
                },
                card_last_four=request.card_last_four,
            )
        except ConflictError:
            # A concurrent request with the same key won the insert; replay its order.
            winner = await self.order_repository.get_by_idempotency_key(
                user_id, request.idempotency_key
            )
            if winner is None:
                # Databases created before keys were per-user still enforce global uniqueness.
                raise
            return OrderResponse.from_order_model(winner)
        logger.info("Created pending order", extra={"order_id": order.id})

        try:
            await self.product_client.reserve_stock(order.product_id, order.quantity)
        except Exception:
            await self._finalize(order, STATUS_FAILED, None)
            raise

        try:
            payment = await self._charge(order, request.card_last_four)
        except PaymentOutcomeUnknownError:
            order.status = STATUS_PAYMENT_UNKNOWN
            await self.order_repository.end_transaction()
            raise
        except Exception:
            await self._finalize(order, STATUS_FAILED, None, release_stock=True)
            raise

        if payment.succeeded:
            order = await self._finalize(order, STATUS_CONFIRMED, payment.id)
            logger.info("Order confirmed", extra={"order_id": order.id, "payment_id": payment.id})
        else:
            order = await self._finalize(order, STATUS_FAILED, None, release_stock=True)
            logger.warning("Order failed: payment declined", extra={"order_id": order.id})

        return OrderResponse.from_order_model(order)

    async def get_order(self, order_id: str, user_id: str) -> OrderResponse:
        order = await self.order_repository.get_by_id(order_id)
        # 404 (not 403) for other users' orders so IDs can't be probed.
        if order is None or order.user_id != user_id:
            raise NotFoundError("Order", order_id)
        return OrderResponse.from_order_model(order)

    async def list_orders(self, user_id: str, skip: int, limit: int) -> OrderListResponse:
        orders, total = await self.order_repository.list_page_by_user(user_id, skip, limit)
        return OrderListResponse(
            orders=[OrderResponse.from_order_model(o) for o in orders],
            total=total,
        )

    async def _charge(self, order: Order, card_last_four: str | None) -> PaymentResult:
        return await self.payment_client.charge(
            order_id=order.id,
            amount=order.total_amount,
            idempotency_key=f"payment-{order.id}",
            card_last_four=card_last_four,
        )

    async def _recover_payment(self, order: Order) -> OrderResponse:
        card_last_four = await self.order_repository.get_payment_card_last_four(order.id)
        await self.order_repository.end_transaction()
        payment = await self._charge(order, card_last_four)
        order = await self.order_repository.lock_for_recovery(order.id)
        if order.status != STATUS_PAYMENT_UNKNOWN:
            return OrderResponse.from_order_model(order)
        status = STATUS_CONFIRMED if payment.succeeded else STATUS_FAILED
        order = await self._finalize(
            order,
            status,
            payment.id if payment.succeeded else None,
            release_stock=not payment.succeeded,
        )
        return OrderResponse.from_order_model(order)

    async def _finalize(
        self, order: Order, status: str, payment_id: str | None, *, release_stock: bool = False
    ) -> Order:
        return await self.order_repository.finalize_with_outbox(
            order,
            status,
            payment_id,
            ORDER_EVENT_TYPE,
            _build_event_payload(order, status, payment_id),
            ORDER_EVENTS_ROUTING_KEY,
            release_stock=release_stock,
        )
