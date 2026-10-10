"""Loading and validation of secrets (JWT signing key, internal service token).

A secret is read from the file named by `<NAME>_FILE` (Docker/Kubernetes
secrets) or, failing that, from the `<NAME>` environment variable. There are
deliberately no defaults: a missing or weak secret must stop the service.

Outside Docker the nearest `.env` is loaded first, so every service sees the
same values whichever config style it uses. Real environment variables win.
"""

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

_DOTENV_PATH = find_dotenv(usecwd=True)
load_dotenv(_DOTENV_PATH)

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


def _resolve_secret_path(file_path: str) -> Path:
    # A relative path is anchored to the directory holding .env, not the cwd,
    # so it works whichever service directory the process was started from.
    path = Path(file_path)
    if path.is_absolute() or not _DOTENV_PATH:
        return path
    return Path(_DOTENV_PATH).parent / path


def read_secret(name: str) -> str:
    """Return the secret from `<name>_FILE` if set, else from `<name>`; "" if neither."""
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        resolved = _resolve_secret_path(file_path)
        try:
            return resolved.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Cannot read {name}_FILE at {str(resolved)!r}: {exc}") from exc
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
