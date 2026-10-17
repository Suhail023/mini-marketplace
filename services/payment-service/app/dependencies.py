"""Composition root: wires repositories into services for each request."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.payment_repository import PaymentRepository
from app.services.payment_service import PaymentService


def get_payment_service(session: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(PaymentRepository(session))
