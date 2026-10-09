"""Loading and validation of secrets (JWT signing key, internal service token).

A secret is read from the file named by `<NAME>_FILE` (Docker/Kubernetes
secrets) or, failing that, from the `<NAME>` environment variable. There are
deliberately no defaults: a missing or weak secret must stop the service.
"""

import os
from pathlib import Path

MIN_SECRET_LENGTH = 32

# Values that have appeared in this repo (and so are public). Never accept them,
# even if someone pads them past the length check.
_KNOWN_PUBLIC_SECRETS = frozenset(
    {
        "change-me-in-production",
        "super-secret-jwt-key-change-in-production",
        "your-jwt-secret-key-change-in-production",
        "your-secret-key-change-in-production",
        "your-internal-service-token-change-in-production",
        "dev-internal-service-token-change-in-production",
    }
)
_PLACEHOLDER_MARKERS = ("change-me", "change-in-production", "changeme", "placeholder")


def read_secret(name: str) -> str:
    """Return the secret from `<name>_FILE` if set, else from `<name>`; "" if neither."""
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        try:
            return Path(file_path).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Cannot read {name}_FILE at {file_path!r}: {exc}") from exc
    return os.getenv(name, "").strip()


def secret_problem(name: str, value: str) -> str | None:
    """Describe why `value` is unacceptable for secret `name`, or None if it's fine."""
    if not value:
        return f"{name} is not set (set {name} or {name}_FILE)"
    lowered = value.lower()
    if lowered in _KNOWN_PUBLIC_SECRETS or any(m in lowered for m in _PLACEHOLDER_MARKERS):
        return f"{name} is a placeholder/publicly known value; generate a new one"
    if len(value) < MIN_SECRET_LENGTH:
        return f"{name} must be at least {MIN_SECRET_LENGTH} characters"
    return None
