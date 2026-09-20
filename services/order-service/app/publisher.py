"""Outbox publisher — background task that polls the outbox table and publishes to RabbitMQ."""

import asyncio
import json

from app.config import get_settings
from app.database import async_session_factory
from app.repositories.outbox_repository import OutboxRepository
from app.utils.logging import setup_logger
from shared.common.rabbitmq import (
    declare_exchange,
    get_connection,
    publish_message,
)

logger = setup_logger(__name__)
settings = get_settings()

POLL_INTERVAL_SECONDS = 2


async def _publish_pending_events() -> None:
    """Poll the outbox table and publish any pending events to RabbitMQ."""
    connection = await get_connection(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        user=settings.RABBITMQ_USER,
        password=settings.RABBITMQ_PASSWORD,
        vhost=settings.RABBITMQ_VHOST,
    )
    exchange = await declare_exchange(connection)

    async with async_session_factory() as session:
        outbox_repo = OutboxRepository(session)
        pending_events = await outbox_repo.get_pending()

        for event in pending_events:
            try:
                payload = json.loads(event.payload)
                await publish_message(
                    exchange=exchange,
                    routing_key=event.routing_key,
                    message=payload,
                    correlation_id=event.id,
                )
                await outbox_repo.mark_published(event.id)
                logger.info(f"Outbox event {event.id} published (type={event.event_type})")
            except Exception:
                logger.exception(f"Failed to publish outbox event {event.id}")
                await outbox_repo.mark_failed(event.id)


async def run_outbox_publisher() -> None:
    """Background loop that continuously drains the outbox table."""
    logger.info("Outbox publisher started")
    while True:
        try:
            await _publish_pending_events()
        except Exception:
            logger.exception("Outbox publisher iteration failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
