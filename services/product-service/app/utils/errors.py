from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ValidationError(AppError):
    def __init__(self, message: str, field: str | None = None):
        details = {"field": field} if field else {}
        super().__init__(message, 400, details)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} with id '{identifier}' not found"
        super().__init__(message, 404, {"resource": resource, "id": identifier})


class ConflictError(AppError):
    def __init__(self, message: str, resource: str | None = None):
        details = {"resource": resource} if resource else {}
        super().__init__(message, 409, details)
