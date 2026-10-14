"""Composition root: wires repositories into services."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService


def build_notification_service(session: AsyncSession) -> NotificationService:
    return NotificationService(NotificationRepository(session))


def get_notification_service(session: AsyncSession = Depends(get_db)) -> NotificationService:
    return build_notification_service(session)
