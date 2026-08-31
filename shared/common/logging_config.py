"""Centralized logging configuration."""

import logging
import sys


def setup_logger(
    name: str, level: str = "INFO", format_string: str | None = None
) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string

    Returns:
        Configured logger instance
    """
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - " "[%(filename)s:%(lineno)d] - %(message)s"
        )

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Only add handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper()))

        formatter = logging.Formatter(format_string)
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger
