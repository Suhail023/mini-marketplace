"""User Service Configuration."""

from functools import lru_cache
from pathlib import Path
import sys

# Add shared modules to path
shared_path = Path(__file__).parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from common.config import BaseServiceConfig


class UserServiceConfig(BaseServiceConfig):
    """Configuration for User Service."""

    SERVICE_NAME: str = "user-service"
    PORT: int = 8001

    # User Service Specific
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_SPECIAL_CHAR: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_UPPERCASE: bool = True

    # Session Management
    SESSION_TIMEOUT_MINUTES: int = 30
    MAX_CONCURRENT_SESSIONS: int = 3

    # Email Verification
    EMAIL_VERIFICATION_REQUIRED: bool = True
    EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS: int = 24

    # Account Lockout
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30


@lru_cache
def get_settings() -> UserServiceConfig:
    """Get cached settings instance."""
    return UserServiceConfig()
