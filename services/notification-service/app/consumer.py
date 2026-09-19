"""RabbitMQ consumer for order events."""

from app.config import get_settings
from app.database import async_session_factory
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService
from app.utils.logging import setup_logger
from shared.common.rabbitmq import consume_messages, get_connection

logger = setup_logger(__name__)
settings = get_settings()

QUEUE_NAME = "notification.order.created"
ROUTING_KEY = "order.created"


async def _handle_order_event(body: dict) -> None:
    """Handle a single incoming OrderCreated event."""
    async with async_session_factory() as session:
        repo = NotificationRepository(session)
        service = NotificationService(repo)
        await service.handle_order_event(body)


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
