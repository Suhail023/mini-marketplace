"""JWT token utilities."""

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.config import get_settings
from common.auth import get_jwt_algorithm, get_jwt_secret_key

settings = get_settings()


def build_token_claims(user_id: str, email: str) -> dict:
    """Claims consumed by every downstream service via common.auth."""
    role = "admin" if user_id in settings.admin_user_ids else "user"
    return {"sub": user_id, "email": email, "role": role}


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_jwt_secret_key(), algorithm=get_jwt_algorithm())
