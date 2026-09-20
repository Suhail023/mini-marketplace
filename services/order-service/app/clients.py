"""HTTP clients for calling Product and Payment services."""

from enum import StrEnum
import time

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.utils.logging import setup_logger
from common.logging_config import get_correlation_id

logger = setup_logger(__name__)
settings = get_settings()

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker for HTTP calls.

    - CLOSED: requests flow through; failures are counted.
    - OPEN: requests are blocked for recovery_timeout seconds.
    - HALF_OPEN: one probe request is allowed through.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker opened",
                extra={"failure_count": self._failure_count},
            )

    def allow_request(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True
        return False


# Module-level singleton shared across the order service.
_payment_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=30)


def _common_headers() -> dict[str, str]:
    """Build headers to forward the correlation ID to downstream services."""
    return {CORRELATION_ID_HEADER: get_correlation_id()}


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open and blocking requests."""


@retry(
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def charge_payment(
    order_id: str,
    amount: float,
    idempotency_key: str,
    card_last_four: str | None = None,
) -> dict:
    """Charge payment via Payment Service with retry and circuit breaker.

    Retry: exponential backoff (1s, 2s, 4s) up to 3 attempts on transient failures.
    Circuit breaker: opens after 5 consecutive failures, half-open after 30s.
    """
    if not _payment_circuit.allow_request():
        logger.warning(
            "Circuit breaker open, skipping payment call",
            extra={"order_id": order_id},
        )
        raise CircuitBreakerOpenError(
            f"Circuit breaker is open for payment service. "
            f"Retry after {_payment_circuit.recovery_timeout}s."
        )

    logger.info(
        "Calling payment service",
        extra={"order_id": order_id, "amount": amount},
    )
    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.PAYMENT_SERVICE_URL}/payments/charge",
                headers=_common_headers(),
                json={
                    "order_id": order_id,
                    "amount": str(amount),
                    "currency": "USD",
                    "idempotency_key": idempotency_key,
                    "card_last_four": card_last_four,
                },
            )
            resp.raise_for_status()
            _payment_circuit.record_success()
            return resp.json()
    except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException):
        _payment_circuit.record_failure()
        raise


async def check_and_reserve_stock(product_id: str, quantity: int) -> dict:
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{settings.PRODUCT_SERVICE_URL}/products/{product_id}/stock/decrement",
            headers=_common_headers(),
            json={"quantity": quantity},
        )
        resp.raise_for_status()
        return resp.json()


async def release_stock(product_id: str, quantity: int) -> dict:
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{settings.PRODUCT_SERVICE_URL}/products/{product_id}/stock/increment",
            headers=_common_headers(),
            json={"quantity": quantity},
        )
        resp.raise_for_status()
        return resp.json()


async def get_product(product_id: str) -> dict:
    async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
        resp = await client.get(
            f"{settings.PRODUCT_SERVICE_URL}/products/{product_id}",
            headers=_common_headers(),
        )
        resp.raise_for_status()
        return resp.json()
