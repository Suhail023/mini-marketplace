"""Notification service — handles incoming order events and persists notifications."""

from app.contracts.notification import NotificationResponse
from app.repositories.notification_repository import NotificationRepository
from app.utils.logging import setup_logger

logger = setup_logger(__name__)


def _build_notification(event: dict) -> dict:
    """Build a notification record from an OrderCreated event payload."""
    status = event.get("status", "unknown")
    order_id = event.get("order_id", "unknown")

    if status == "confirmed":
        title = "Order Confirmed"
        message = (
            f"Your order #{order_id[:8]} has been confirmed. "
            f"Total: ${event.get('total_amount', 0):.2f}. "
            f"Thank you for your purchase!"
        )
    else:
        title = "Order Failed"
        message = (
            f"Your order #{order_id[:8]} could not be processed. "
            f"Payment was not successful. Please try again."
        )

    return {
        "event_id": event.get("event_id", ""),
        "order_id": order_id,
        "user_id": event.get("user_id", ""),
        "type": f"order.{status}",
        "title": title,
        "message": message,
        "status": "sent",
    }


class NotificationService:
    def __init__(self, notification_repository: NotificationRepository):
        self.notification_repository = notification_repository

    async def handle_order_event(self, event: dict) -> NotificationResponse:
        """Process an OrderCreated event and persist a notification.

        Deduplicates by event_id — if this event was already processed,
        the existing notification is returned.
        """
        event_id = event.get("event_id", "")

        existing = await self.notification_repository.get_by_event_id(event_id)
        if existing:
            logger.info(f"Duplicate event {event_id} — returning existing notification")
            return NotificationResponse(
                id=existing.id,
                event_id=existing.event_id,
                order_id=existing.order_id,
                user_id=existing.user_id,
                type=existing.type,
                title=existing.title,
                message=existing.message,
                status=existing.status,
                created_at=existing.created_at,
                sent_at=existing.sent_at,
            )

        notification_data = _build_notification(event)
        notification = await self.notification_repository.create(notification_data)
        logger.info(
            f"Notification {notification.id} created for order {notification.order_id} "
            f"(event={event_id})"
        )

        return NotificationResponse(
            id=notification.id,
            event_id=notification.event_id,
            order_id=notification.order_id,
            user_id=notification.user_id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            status=notification.status,
            created_at=notification.created_at,
            sent_at=notification.sent_at,
        )

    async def get_notification(self, notification_id: str) -> NotificationResponse | None:
        notification = await self.notification_repository.get_by_id(notification_id)
        if not notification:
            return None
        return NotificationResponse(
            id=notification.id,
            event_id=notification.event_id,
            order_id=notification.order_id,
            user_id=notification.user_id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            status=notification.status,
            created_at=notification.created_at,
            sent_at=notification.sent_at,
        )

    async def list_notifications(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> list[NotificationResponse]:
        notifications = await self.notification_repository.list_by_user(
            user_id, skip=skip, limit=limit
        )
        return [
            NotificationResponse(
                id=n.id,
                event_id=n.event_id,
                order_id=n.order_id,
                user_id=n.user_id,
                type=n.type,
                title=n.title,
                message=n.message,
                status=n.status,
                created_at=n.created_at,
                sent_at=n.sent_at,
            )
            for n in notifications
        ]
