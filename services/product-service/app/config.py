from dataclasses import dataclass, field
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    HOST: str = os.getenv("DATABASE_HOST", "localhost")
    PORT: int = int(os.getenv("DATABASE_PORT", "5432"))
    USER: str = os.getenv("DATABASE_USER", "postgres")
    PASSWORD: str = os.getenv("DATABASE_PASSWORD", "postgres")
    NAME: str = os.getenv("DATABASE_NAME", "productdb")

    POOL_SIZE: int = int(os.getenv("SQLALCHEMY_POOL_SIZE", "10"))
    MAX_OVERFLOW: int = int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "20"))
    POOL_RECYCLE: int = int(os.getenv("SQLALCHEMY_POOL_RECYCLE", "3600"))
    POOL_PRE_PING: bool = os.getenv("SQLALCHEMY_POOL_PRE_PING", "true").lower() == "true"

    @property
    def url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}"
            f"@{self.HOST}:{self.PORT}/{self.NAME}"
        )

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.USER}:{self.PASSWORD}" f"@{self.HOST}:{self.PORT}/{self.NAME}"


@dataclass
class RedisConfig:
    URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")


@dataclass
class Config:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)

    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "product-service")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", "8002"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")

    CORS_ORIGINS: list[str] = field(
        default_factory=lambda: (
            os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
        )
    )

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT in ("staging", "release")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT in ("production", "prod")


def get_settings() -> Config:
    return Config()
