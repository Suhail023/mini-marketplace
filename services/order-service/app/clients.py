"""HTTP adapters for the Product and Payment services.

Each client translates transport failures and downstream status codes into
AppError subclasses, so the service layer never sees httpx.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.utils.errors import AppError, ConflictError, NotFoundError, ServiceUnavailableError
from app.utils.logging import setup_logger
from common.auth import internal_auth_headers
from common.logging_config import get_correlation_id

logger = setup_logger(__name__)

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


@dataclass(frozen=True)
class ProductInfo:
    id: str
    price: Decimal


@dataclass(frozen=True)
class PaymentResult:
    id: str | None
    status: str

    @property
    def succeeded(self) -> bool:
        return self.status == "succeeded"


def _common_headers() -> dict[str, str]:
    return {CORRELATION_ID_HEADER: get_correlation_id()}


def _internal_headers() -> dict[str, str]:
    return {**_common_headers(), **internal_auth_headers()}


def _is_transient(exc: BaseException) -> bool:
    """Network errors, timeouts and 5xx are worth retrying; 4xx never succeed on retry."""
    if isinstance(exc, httpx.ConnectError | httpx.TimeoutException):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


def _status_of(exc: httpx.HTTPError) -> int | None:
    return exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None


class ProductClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url
        self.timeout = timeout

    async def get_product(self, product_id: str) -> ProductInfo:
        try:
            data = await self._request("GET", f"/products/{product_id}", headers=_common_headers())
        except httpx.HTTPError as exc:
            if _status_of(exc) == 404:
                raise NotFoundError("Product", product_id)
            raise self._unavailable("fetch product", exc)

        price = data.get("price")
        if not isinstance(price, int | float) or price <= 0:
            logger.error(
                "Product service returned an invalid price",
                extra={"product_id": product_id, "price": price},
            )
            raise AppError(f"Product '{product_id}' has no valid price", 502)
        return ProductInfo(id=product_id, price=Decimal(str(price)))

    async def reserve_stock(self, product_id: str, quantity: int) -> None:
        try:
            await self._request(
                "POST",
                f"/internal/products/{product_id}/stock/decrement",
                headers=_internal_headers(),
                json={"quantity": quantity},
            )
        except httpx.HTTPError as exc:
            status = _status_of(exc)
            if status == 404:
                raise NotFoundError("Product", product_id)
            if status == 409:
                raise ConflictError(f"Insufficient stock for product '{product_id}'", "stock")
            raise self._unavailable("reserve stock", exc)

    async def release_stock(self, product_id: str, quantity: int) -> None:
        try:
            await self._request(
                "POST",
                f"/internal/products/{product_id}/stock/increment",
                headers=_internal_headers(),
                json={"quantity": quantity},
            )
        except httpx.HTTPError as exc:
            raise self._unavailable("release stock", exc)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _unavailable(action: str, exc: httpx.HTTPError) -> ServiceUnavailableError:
        logger.error(f"Product service failed to {action}", extra={"error": repr(exc)})
        return ServiceUnavailableError("Product service is unavailable")


class PaymentClient:
    """Charges via the Payment Service with retry and a circuit breaker.

    Retry: up to 3 attempts with exponential backoff (1s, 2s) on connection errors,
    timeouts and 5xx. Safe because every attempt sends the same idempotency key.
    Circuit breaker: counts one failure per charge() call (after retries are
    exhausted), opens after 5 consecutive failed calls, half-opens after 30s.
    """

    def __init__(self, base_url: str, timeout: float, circuit: CircuitBreaker) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.circuit = circuit

    async def charge(
        self,
        order_id: str,
        amount: Decimal,
        idempotency_key: str,
        card_last_four: str | None = None,
    ) -> PaymentResult:
        if not self.circuit.allow_request():
            logger.warning(
                "Circuit breaker open, skipping payment call", extra={"order_id": order_id}
            )
            raise ServiceUnavailableError(
                f"Payment service is unavailable. Retry after {self.circuit.recovery_timeout}s."
            )

        logger.info("Calling payment service", extra={"order_id": order_id, "amount": str(amount)})
        try:
            data = await self._post_charge(
                {
                    "order_id": order_id,
                    "amount": str(amount),
                    "currency": "USD",
                    "idempotency_key": idempotency_key,
                    "card_last_four": card_last_four,
                }
            )
        except httpx.HTTPError as exc:
            if _is_transient(exc):
                self.circuit.record_failure()
                logger.error("Payment service unavailable", extra={"error": repr(exc)})
                raise ServiceUnavailableError("Payment service is unavailable")
            # Payment service responded (e.g. 4xx), so it is healthy.
            self.circuit.record_success()
            logger.error("Payment service rejected the charge", extra={"error": repr(exc)})
            raise AppError("Payment could not be processed", 502)

        self.circuit.record_success()
        return PaymentResult(id=data.get("id"), status=str(data.get("status")))

    @retry(
        retry=retry_if_exception(_is_transient),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        stop=stop_after_attempt(PAYMENT_MAX_ATTEMPTS),
        reraise=True,
    )
    async def _post_charge(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post(
                "/internal/payments/charge", headers=_internal_headers(), json=payload
            )
            resp.raise_for_status()
            return resp.json()
