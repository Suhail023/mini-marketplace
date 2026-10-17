"""Composition root: process-wide clients plus per-request repository/service wiring."""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import CircuitBreaker, PaymentClient, ProductClient
from app.config import get_settings
from app.database import get_db
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService


@lru_cache
def get_product_client() -> ProductClient:
    settings = get_settings()
    return ProductClient(settings.PRODUCT_SERVICE_URL, settings.HTTP_TIMEOUT)


@lru_cache
def get_payment_client() -> PaymentClient:
    # One breaker per process so failures from every request share the same state.
    settings = get_settings()
    return PaymentClient(
        settings.PAYMENT_SERVICE_URL,
        settings.PAYMENT_HTTP_TIMEOUT,
        CircuitBreaker(failure_threshold=5, recovery_timeout=30),
    )


def get_order_service(
    session: AsyncSession = Depends(get_db),
    product_client: ProductClient = Depends(get_product_client),
    payment_client: PaymentClient = Depends(get_payment_client),
) -> OrderService:
    return OrderService(OrderRepository(session), product_client, payment_client)
