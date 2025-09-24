"""Security helpers shared across the application."""

from __future__ import annotations

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using the configured crypt context."""

    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""

    return pwd_context.verify(plain_password, password_hash)


__all__ = ["hash_password", "verify_password", "pwd_context"]
