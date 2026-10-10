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

from common.logging_config import setup_logger
from common.secrets import read_secret, secret_problem

logger = setup_logger(__name__)

INTERNAL_TOKEN_HEADER = "X-Internal-Token"
ROLE_ADMIN = "admin"
ROLE_USER = "user"

# auto_error=False so a missing header yields 401 (FastAPI's default is 403).
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    """The authenticated end user, derived solely from a verified JWT."""

    user_id: str
    email: str | None
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


# Each secret is read on its own so a service never fails on one it doesn't use.
@lru_cache
def get_jwt_secret_key() -> str:
    return read_secret("JWT_SECRET_KEY")


@lru_cache
def get_internal_service_token() -> str:
    return read_secret("INTERNAL_SERVICE_TOKEN")


def get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def validate_auth_settings(*, jwt: bool = False, internal_token: bool = False) -> None:
    """Fail fast at startup if a secret this service depends on is missing or weak."""
    problems = []
    if jwt:
        problems.append(secret_problem("JWT_SECRET_KEY", get_jwt_secret_key()))
        if get_jwt_algorithm() not in ("HS256", "HS384", "HS512"):
            problems.append(f"JWT_ALGORITHM {get_jwt_algorithm()!r} is not an HMAC algorithm")
    if internal_token:
        problems.append(secret_problem("INTERNAL_SERVICE_TOKEN", get_internal_service_token()))
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
    # Imported here so services that only use the internal token don't need jose.
    from jose import JWTError, jwt

    secret_key = get_jwt_secret_key()
    if not secret_key:
        # Never verify against an empty key; that would accept forged tokens.
        logger.error("JWT_SECRET_KEY is not configured; rejecting request")
        raise _unauthorized("Invalid or expired token")
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[get_jwt_algorithm()],
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
    expected = get_internal_service_token()
    if not expected or not token or not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service credentials",
        )


def internal_auth_headers() -> dict[str, str]:
    """Headers a service attaches when calling another service's /internal/* API."""
    return {INTERNAL_TOKEN_HEADER: get_internal_service_token()}
