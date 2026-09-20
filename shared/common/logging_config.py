"""Centralized logging configuration with structured JSON and correlation ID support."""

from contextvars import ContextVar
import json
import logging
import sys

CORRELATION_ID_VAR: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return CORRELATION_ID_VAR.get()


def set_correlation_id(cid: str) -> None:
    CORRELATION_ID_VAR.set(cid)


class CorrelationFilter(logging.Filter):
    """Inject correlation_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter with correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, str | int | float | None] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def setup_logger(name: str, level: str = "INFO", json_format: bool = True) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use structured JSON formatting

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper()))

        if json_format:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
            )

        handler.setFormatter(formatter)
        handler.addFilter(CorrelationFilter())
        logger.addHandler(handler)

    return logger
