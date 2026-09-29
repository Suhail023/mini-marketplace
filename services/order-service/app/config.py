"""Order Service configuration."""

from dataclasses import dataclass, field
import os


@dataclass
class DatabaseConfig:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    HOST: str = os.getenv("DATABASE_HOST", "localhost")
    PORT: int = int(os.getenv("DATABASE_PORT", "5432"))
    USER: str = os.getenv("DATABASE_USER", "postgres")
    PASSWORD: str = os.getenv("DATABASE_PASSWORD", "postgres")
    NAME: str = os.getenv("DATABASE_NAME", "orderdb")

    @property
    def url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"
        )


@dataclass
class Config:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "order-service")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", "8003"))

    # Service URLs (use Docker service names)
    PRODUCT_SERVICE_URL: str = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8002")
    PAYMENT_SERVICE_URL: str = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8004")

    # HTTP client timeouts
    HTTP_TIMEOUT: float = float(os.getenv("HTTP_TIMEOUT", "10.0"))
    # Per-attempt timeout for payment calls. Worst case with retries is
    # 3 * 5s + 1s + 2s backoff = 18s, which stays under the gateway's 30s read timeout.
    PAYMENT_HTTP_TIMEOUT: float = float(os.getenv("PAYMENT_HTTP_TIMEOUT", "5.0"))

    # RabbitMQ
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")

    CORS_ORIGINS: list[str] = field(
        default_factory=lambda: (
            os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
        )
    )


def get_settings() -> Config:
    return Config()
