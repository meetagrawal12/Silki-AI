"""
Password hashing and JWT issuing/verification.

Kept deliberately separate from the auth *service* (which deals with users
and the database) — this module only knows about cryptography, nothing
about your data model. That separation is what makes it testable in
isolation and reusable if the user model ever changes.
"""
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

TokenType = Literal["access", "refresh"]

# bcrypt has a hard 72-byte input limit; truncate deliberately (rather than
# letting the library raise) so long passphrases fail loudly at signup, not
# cryptically at login.
_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_token(subject: str, token_type: TokenType) -> str:
    """Create a signed JWT for the given user id (subject)."""
    now = datetime.now(timezone.utc)
    if token_type == "access":
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    else:
        expire = now + timedelta(days=settings.refresh_token_expire_days)

    payload = {"sub": subject, "type": token_type, "iat": now, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    """Return the decoded payload, or None if invalid/expired."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
