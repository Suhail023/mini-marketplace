"""Application error hierarchy and the handlers that render it as one JSON envelope.

Services raise AppError subclasses from the service layer; the handlers registered
by register_error_handlers() turn them, request-validation failures, HTTPExceptions
and anything unexpected into:

    {"error": {"message": str, "type": str, "details": dict}}

Unexpected exceptions are logged and returned as a generic 500 so stack traces,
SQL and internal URLs never reach a client.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.logging_config import setup_logger

logger = setup_logger(__name__)


class AppError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ValidationError(AppError):
    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, 400, {"field": field} if field else None)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, 401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, 403)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            f"{resource} with id '{identifier}' not found",
            404,
            {"resource": resource, "id": identifier},
        )


class ConflictError(AppError):
    def __init__(self, message: str, resource: str | None = None) -> None:
        super().__init__(message, 409, {"resource": resource} if resource else None)


class ServiceUnavailableError(AppError):
    def __init__(self, message: str = "A downstream service is unavailable") -> None:
        super().__init__(message, 503)


def _envelope(
    status_code: int,
    error_type: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": error_type, "details": details or {}}},
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _envelope(exc.status_code, type(exc).__name__, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _envelope(
            422,
            "ValidationError",
            "Request validation failed",
            {"errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _envelope(exc.status_code, "HTTPError", str(exc.detail), headers=exc.headers)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", extra={"path": request.url.path})
        return _envelope(500, "InternalServerError", "Internal server error")
