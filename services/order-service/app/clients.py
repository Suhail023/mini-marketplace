"""HTTP clients for calling Product and Payment services."""

import httpx

from app.config import get_settings

settings = get_settings()


async def check_and_reserve_stock(product_id: str, quantity: int) -> dict:
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{settings.PRODUCT_SERVICE_URL}/products/{product_id}/stock/decrement",
            json={"quantity": quantity},
        )
        resp.raise_for_status()
        return resp.json()


async def get_product(product_id: str) -> dict:
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.get(f"{settings.PRODUCT_SERVICE_URL}/products/{product_id}")
        resp.raise_for_status()
        return resp.json()


async def charge_payment(
    order_id: str,
    amount: float,
    idempotency_key: str,
    card_last_four: str | None = None,
) -> dict:
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{settings.PAYMENT_SERVICE_URL}/payments/charge",
            json={
                "order_id": order_id,
                "amount": amount,
                "currency": "USD",
                "idempotency_key": idempotency_key,
                "card_last_four": card_last_four,
            },
        )
        resp.raise_for_status()
        return resp.json()
