"""Notification Service — consumes order events from RabbitMQ."""

from app.utils.logging import setup_logger

logger = setup_logger(__name__)
