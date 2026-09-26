"""HTTP clients for calling Product and Payment services."""

from enum import StrEnum
import time

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.utils.logging import setup_logger
from common.logging_config import get_correlation_id

logger = setup_logger(__name__)
settings = get_settings()

CORRELATION_ID_HEADER = "X-Correlation-ID"

PAYMENT_MAX_ATTEMPTS = 3


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker for HTTP calls.

    - CLOSED: requests flow through; consecutive failures are counted.
    - OPEN: requests are blocked for recovery_timeout seconds.
    - HALF_OPEN: exactly one probe request is allowed through; its outcome
      closes the circuit (success) or re-opens it (failure).
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._probe_in_flight = False

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        self._probe_in_flight = False
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        was_probe = self._probe_in_flight
        self._probe_in_flight = False
        if was_probe or self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker opened",
                extra={"failure_count": self._failure_count},
            )

    def allow_request(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN and not self._probe_in_flight:
            self._probe_in_flight = True
            return True
        return False


# Module-level singleton shared across the order service.
_payment_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=30)


def _common_headers() -> dict[str, str]:
    """Build headers to forward the correlation ID to downstream services."""
    return {CORRELATION_ID_HEADER: get_correlation_id()}


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open and blocking requests."""


def _is_transient(exc: BaseException) -> bool:
    """Network errors, timeouts and 5xx are worth retrying; 4xx never succeed on retry."""
    if isinstance(exc, httpx.ConnectError | httpx.TimeoutException):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


@retry(
    retry=retry_if_exception(_is_transient),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    stop=stop_after_attempt(PAYMENT_MAX_ATTEMPTS),
    reraise=True,
)
async def _post_charge(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=settings.PAYMENT_HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{settings.PAYMENT_SERVICE_URL}/payments/charge",
            headers=_common_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def charge_payment(
    order_id: str,
    amount: float,
    idempotency_key: str,
    card_last_four: str | None = None,
) -> dict:
    """Charge payment via Payment Service with retry and circuit breaker.

    Retry: up to 3 attempts with exponential backoff (1s, 2s) on connection errors,
    timeouts and 5xx. Safe because every attempt sends the same idempotency key.
    Circuit breaker: counts one failure per charge_payment call (after retries are
    exhausted), opens after 5 consecutive failed calls, half-opens after 30s.
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
        result = await _post_charge(
            {
                "order_id": order_id,
                "amount": str(amount),
                "currency": "USD",
                "idempotency_key": idempotency_key,
                "card_last_four": card_last_four,
            }
        )
    except Exception as exc:
        if _is_transient(exc):
            _payment_circuit.record_failure()
        else:
            # Payment service responded (e.g. 4xx), so it is healthy.
            _payment_circuit.record_success()
        raise
    _payment_circuit.record_success()
    return result


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
