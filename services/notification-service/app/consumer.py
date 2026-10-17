"""RabbitMQ consumer for order events."""

from typing import Any

from app.config import get_settings
from app.database import db
from app.dependencies import build_notification_service
from app.utils.logging import setup_logger
from common.rabbitmq import consume_messages, get_connection
from shared.events.order import OrderCreatedEvent

logger = setup_logger(__name__)
settings = get_settings()

QUEUE_NAME = "notification.order.created"
ROUTING_KEY = "order.created"


async def _handle_order_event(body: dict[str, Any]) -> None:
    # A malformed event raises here and is dead-lettered by consume_messages.
    event = OrderCreatedEvent.model_validate(body)
    async with db.session() as session:
        await build_notification_service(session).handle_order_event(event)


async def run_consumer() -> None:
    """Connect to RabbitMQ and consume order events indefinitely."""
    logger.info("Notification consumer starting")

    connection = await get_connection(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        user=settings.RABBITMQ_USER,
        password=settings.RABBITMQ_PASSWORD,
        vhost=settings.RABBITMQ_VHOST,
    )

    await consume_messages(
        connection=connection,
        queue_name=QUEUE_NAME,
        routing_key=ROUTING_KEY,
        handler=_handle_order_event,
    )
