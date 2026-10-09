"""JWT token utilities."""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.config import get_settings
from common.auth import get_auth_settings

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
    auth = get_auth_settings()
    return jwt.encode(to_encode, auth.jwt_secret_key, algorithm=auth.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        auth = get_auth_settings()
        payload = jwt.decode(token, auth.jwt_secret_key, algorithms=[auth.jwt_algorithm])
        return payload
    except JWTError:
        return None
