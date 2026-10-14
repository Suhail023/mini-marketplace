"""Outbox publisher — background task that drains the outbox table into RabbitMQ."""

import asyncio
import json

import aio_pika

from app.config import get_settings
from app.database import db
from app.repositories.outbox_repository import OutboxRepository
from app.utils.logging import setup_logger
from common.rabbitmq import declare_exchange, get_connection, publish_message

logger = setup_logger(__name__)
settings = get_settings()

POLL_INTERVAL_SECONDS = 2


class OutboxPublisher:
    def __init__(self) -> None:
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def _get_exchange(self) -> aio_pika.abc.AbstractExchange:
        # Reuse one channel across polls; declaring per poll leaks a channel every cycle.
        if self._exchange is None or self._exchange.channel.is_closed:
            connection = await get_connection(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                user=settings.RABBITMQ_USER,
                password=settings.RABBITMQ_PASSWORD,
                vhost=settings.RABBITMQ_VHOST,
            )
            self._exchange = await declare_exchange(connection)
        return self._exchange

    async def publish_unpublished(self) -> None:
        exchange = await self._get_exchange()
        async with db.session() as session:
            outbox = OutboxRepository(session)
            for event in await outbox.get_unpublished():
                try:
                    await publish_message(
                        exchange=exchange,
                        routing_key=event.routing_key,
                        message=json.loads(event.payload),
                        correlation_id=event.id,
                    )
                    await outbox.mark_published(event.id)
                    logger.info(
                        "Outbox event published",
                        extra={"event_id": event.id, "event_type": event.event_type},
                    )
                except Exception:
                    logger.exception("Failed to publish outbox event", extra={"event_id": event.id})
                    await outbox.mark_failed(event.id)

    async def run(self) -> None:
        logger.info("Outbox publisher started")
        while True:
            try:
                await self.publish_unpublished()
            except Exception:
                logger.exception("Outbox publisher iteration failed")
                self._exchange = None
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
