"""RabbitMQ connection and publisher utilities using aio-pika."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
import json
from typing import Any

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from shared.common.logging_config import setup_logger

logger = setup_logger(__name__)

_connection: AbstractRobustConnection | None = None
_connection_lock = asyncio.Lock()

EXCHANGE_NAME = "marketplace.events"
ORDER_EVENTS_ROUTING_KEY = "order.created"


async def get_connection(
    host: str = "localhost",
    port: int = 5672,
    user: str = "guest",
    password: str = "guest",  # noqa: S107
    vhost: str = "/",
) -> AbstractRobustConnection:
    """Return a shared, lazily-initialized RabbitMQ connection."""
    global _connection
    if _connection is not None and not _connection.is_closed:
        return _connection

    async with _connection_lock:
        if _connection is not None and not _connection.is_closed:
            return _connection

        url = f"amqp://{user}:{password}@{host}:{port}/{vhost}"
        _connection = await aio_pika.connect_robust(url, loop=asyncio.get_event_loop())
        logger.info(f"RabbitMQ connected to {host}:{port}")
        return _connection


async def declare_exchange(connection: AbstractRobustConnection) -> aio_pika.Exchange:
    """Declare the topic exchange used for domain events."""
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    return exchange


async def publish_message(
    exchange: aio_pika.Exchange,
    routing_key: str,
    message: dict[str, Any],
    correlation_id: str | None = None,
) -> None:
    """Publish a JSON message to the given exchange and routing key."""
    body = json.dumps(message, default=str).encode()
    amqp_message = aio_pika.Message(
        body,
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        correlation_id=correlation_id,
    )
    await exchange.publish(amqp_message, routing_key=routing_key)
    logger.info(f"Published message to {routing_key}: {correlation_id}")


async def consume_messages(
    connection: AbstractRobustConnection,
    queue_name: str,
    routing_key: str,
    handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
) -> None:
    """Bind a queue to the exchange and consume messages with the given handler.

    The handler receives the parsed JSON body of each message.
    Messages are acknowledged after the handler returns successfully.
    Dead-letter routing is configured with a DLX.
    """
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    dlx_exchange = await channel.declare_exchange(
        f"{EXCHANGE_NAME}.dlx",
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    dlq = await channel.declare_queue(f"{queue_name}.dlq", durable=True)
    await dlq.bind(dlx_exchange, routing_key=routing_key)

    queue = await channel.declare_queue(
        queue_name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": f"{EXCHANGE_NAME}.dlx",
            "x-dead-letter-routing-key": routing_key,
        },
    )
    await queue.bind(exchange, routing_key=routing_key)

    logger.info(f"Consuming from queue '{queue_name}' (routing key: {routing_key})")

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process(requeue=False):
                try:
                    body = json.loads(message.body.decode())
                    await handler(body)
                    logger.info(
                        f"Processed message {message.correlation_id or 'N/A'} "
                        f"from queue '{queue_name}'"
                    )
                except Exception:
                    logger.exception(
                        f"Failed to process message {message.correlation_id or 'N/A'} "
                        f"from queue '{queue_name}' — sending to DLQ"
                    )
                    raise
