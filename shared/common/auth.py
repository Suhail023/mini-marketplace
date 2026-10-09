"""Shared authentication for downstream services.

Two independent mechanisms:

- End-user auth: a bearer JWT issued by user-service. The caller's identity is
  always taken from the token's `sub` claim, never from the request body/path.
- Service-to-service auth: a shared secret sent in `X-Internal-Token`. Used only
  by `/internal/*` endpoints, which the gateway does not route.
"""

from dataclasses import dataclass
from functools import lru_cache
import hmac
import os

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from common.logging_config import setup_logger
from common.secrets import read_secret, secret_problem

logger = setup_logger(__name__)

INTERNAL_TOKEN_HEADER = "X-Internal-Token"
ROLE_ADMIN = "admin"
ROLE_USER = "user"

# auto_error=False so a missing header yields 401 (FastAPI's default is 403).
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthSettings:
    jwt_secret_key: str
    jwt_algorithm: str
    internal_service_token: str


@dataclass(frozen=True)
class Principal:
    """The authenticated end user, derived solely from a verified JWT."""

    user_id: str
    email: str | None
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings(
        jwt_secret_key=read_secret("JWT_SECRET_KEY"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        internal_service_token=read_secret("INTERNAL_SERVICE_TOKEN"),
    )


def validate_auth_settings(*, jwt: bool = False, internal_token: bool = False) -> None:
    """Fail fast at startup if a secret this service depends on is missing or weak."""
    settings = get_auth_settings()
    problems = []
    if jwt:
        problems.append(secret_problem("JWT_SECRET_KEY", settings.jwt_secret_key))
        if settings.jwt_algorithm not in ("HS256", "HS384", "HS512"):
            problems.append(f"JWT_ALGORITHM {settings.jwt_algorithm!r} is not an HMAC algorithm")
    if internal_token:
        problems.append(secret_problem("INTERNAL_SERVICE_TOKEN", settings.internal_service_token))
    problems = [p for p in problems if p]
    if problems:
        raise RuntimeError("Invalid auth configuration: " + "; ".join(problems))


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_principal(token: str) -> Principal:
    settings = get_auth_settings()
    if not settings.jwt_secret_key:
        # Never verify against an empty key; that would accept forged tokens.
        logger.error("JWT_SECRET_KEY is not configured; rejecting request")
        raise _unauthorized("Invalid or expired token")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require_exp": True, "require_sub": True},
        )
    except JWTError:
        raise _unauthorized("Invalid or expired token")

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise _unauthorized("Token missing subject claim")

    return Principal(
        user_id=user_id,
        email=payload.get("email"),
        role=payload.get("role", ROLE_USER),
    )


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if credentials is None:
        raise _unauthorized("Not authenticated")
    return decode_principal(credentials.credentials)


async def require_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return principal


async def require_internal_service(
    token: str | None = Header(None, alias=INTERNAL_TOKEN_HEADER),
) -> None:
    expected = get_auth_settings().internal_service_token
    if not expected or not token or not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service credentials",
        )


def internal_auth_headers() -> dict[str, str]:
    """Headers a service attaches when calling another service's /internal/* API."""
    return {INTERNAL_TOKEN_HEADER: get_auth_settings().internal_service_token}
