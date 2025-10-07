"""Security helpers shared across the application."""

from __future__ import annotations

from passlib import exc as passlib_exc
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using the configured crypt context."""

    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""

    try:
        return pwd_context.verify(plain_password, password_hash)
    except passlib_exc.UnknownHashError:
        return False


def is_password_hash(value: str | None) -> bool:
    """Return ``True`` if *value* looks like a supported password hash."""

    if not value:
        return False

    try:
        return pwd_context.identify(value) is not None
    except ValueError:
        return False


__all__ = ["hash_password", "verify_password", "pwd_context", "is_password_hash"]
