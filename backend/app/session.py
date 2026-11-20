"""Anonymous session identity via a signed, httpOnly cookie."""

import os
import secrets
from pathlib import Path

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

COOKIE_NAME = "pomidorai_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 2  # 2 years
_SALT = "pomidorai-session"

_SECRET_FILE = Path(__file__).parent.parent / "data" / "secret.key"


def _load_secret() -> str:
    """Load the signing secret, generating and persisting one on first run."""
    env_secret = os.environ.get("POMIDORAI_SECRET")
    if env_secret:
        return env_secret

    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text().strip()

    secret = secrets.token_urlsafe(48)
    _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_FILE.write_text(secret)
    _SECRET_FILE.chmod(0o600)
    return secret


_serializer = URLSafeSerializer(_load_secret(), salt=_SALT)


def sign(session_id: str) -> str:
    return _serializer.dumps(session_id)


def unsign(value: str) -> str | None:
    try:
        return _serializer.loads(value)
    except BadSignature:
        return None


def read_session(request: Request) -> str | None:
    """Return the session id from a validly signed cookie, else None."""
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    return unsign(raw)


def ensure_session(request: Request, response: Response) -> str:
    """Return the caller's session id, minting and setting one if absent."""
    existing = read_session(request)
    if existing:
        return existing

    session_id = secrets.token_urlsafe(32)
    response.set_cookie(
        COOKIE_NAME,
        sign(session_id),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return session_id
