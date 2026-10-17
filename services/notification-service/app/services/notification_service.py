"""Notification service — handles incoming order events and persists notifications."""

from typing import Any

from app.contracts.notification import NotificationListResponse, NotificationResponse
from app.repositories.notification_repository import NotificationRepository
from app.utils.errors import ConflictError, NotFoundError
from app.utils.logging import setup_logger
from shared.events.order import OrderCreatedEvent

logger = setup_logger(__name__)


def _build_notification(event: OrderCreatedEvent) -> dict[str, Any]:
    short_id = event.order_id[:8]
    if event.status == "confirmed":
        title = "Order Confirmed"
        message = (
            f"Your order #{short_id} has been confirmed. "
            f"Total: ${event.total_amount:.2f}. "
            f"Thank you for your purchase!"
        )
    else:
        title = "Order Failed"
        message = (
            f"Your order #{short_id} could not be processed. "
            f"Payment was not successful. Please try again."
        )

    return {
        "event_id": event.event_id,
        "order_id": event.order_id,
        "user_id": event.user_id,
        "type": f"order.{event.status}",
        "title": title,
        "message": message,
        "status": "sent",
    }


class NotificationService:
    def __init__(self, notification_repository: NotificationRepository) -> None:
        self.notification_repository = notification_repository

    async def handle_order_event(self, event: OrderCreatedEvent) -> NotificationResponse:
        """Persist a notification for the event, deduplicating redeliveries by event_id."""
        existing = await self.notification_repository.get_by_event_id(event.event_id)
        if existing:
            logger.info("Duplicate event ignored", extra={"event_id": event.event_id})
            return NotificationResponse.from_notification_model(existing)

        try:
            notification = await self.notification_repository.create(_build_notification(event))
        except ConflictError:
            winner = await self.notification_repository.get_by_event_id(event.event_id)
            if winner is None:
                raise
            return NotificationResponse.from_notification_model(winner)

        logger.info(
            "Notification created",
            extra={"notification_id": notification.id, "event_id": event.event_id},
        )
        return NotificationResponse.from_notification_model(notification)

    async def get_notification(self, notification_id: str, user_id: str) -> NotificationResponse:
        notification = await self.notification_repository.get_by_id(notification_id)
        # 404 (not 403) for other users' notifications so IDs can't be probed.
        if notification is None or notification.user_id != user_id:
            raise NotFoundError("Notification", notification_id)
        return NotificationResponse.from_notification_model(notification)

    async def list_notifications(
        self, user_id: str, skip: int, limit: int
    ) -> NotificationListResponse:
        notifications, total = await self.notification_repository.list_page_by_user(
            user_id, skip, limit
        )
        return NotificationListResponse(
            notifications=[NotificationResponse.from_notification_model(n) for n in notifications],
            total=total,
        )
