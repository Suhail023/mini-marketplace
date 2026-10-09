"""Generate the Docker secrets used by docker-compose.yml.

Usage:
    python scripts/generate_secrets.py           # create any missing secrets
    python scripts/generate_secrets.py --rotate  # replace all secrets

Rotating the JWT key invalidates every issued token (users must log in again).
Restart the services after rotating: docker compose up -d --force-recreate
"""

import argparse
from pathlib import Path
import secrets

SECRETS_DIR = Path(__file__).resolve().parent.parent / "secrets"
SECRET_NAMES = ("jwt_secret_key", "internal_service_token")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rotate", action="store_true", help="overwrite existing secrets")
    args = parser.parse_args()

    SECRETS_DIR.mkdir(exist_ok=True)
    for name in SECRET_NAMES:
        path = SECRETS_DIR / name
        if path.exists() and not args.rotate:
            print(f"kept      {path} (use --rotate to replace)")
            continue
        path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        path.chmod(0o600)
        print(f"generated {path}")


if __name__ == "__main__":
    main()
