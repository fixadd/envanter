from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password, pwd_context, verify_password
from models import User


_TURKISH_UPPER_REPLACEMENTS = {
    "İ": "I",
    "İ": "I",
    "Ş": "S",
    "Ğ": "G",
    "Ü": "U",
    "Ö": "O",
    "Ç": "C",
}

_TURKISH_LOWER_REPLACEMENTS = {
    "ı": "i",
    "ş": "s",
    "ğ": "g",
    "ü": "u",
    "ö": "o",
    "ç": "c",
    "̇": "",
}


def get_user_by_username(db: Session, username: str) -> User | None:
    normalized = _normalize_username(username)
    if not normalized:
        return None

    return db.query(User).filter(_normalized_username_column() == normalized).first()


def _normalize_username(value: str | None) -> str:
    """Return a case-insensitive, accent-free representation of *value*."""

    if not value:
        return ""

    normalized = value.strip().casefold()
    for search, replacement in _TURKISH_LOWER_REPLACEMENTS.items():
        normalized = normalized.replace(search, replacement)
    return normalized


def _normalized_username_column():
    """Return a SQL expression mirroring :func:`_normalize_username`."""

    column = func.trim(User.username)
    for search, replacement in _TURKISH_UPPER_REPLACEMENTS.items():
        column = func.replace(column, search, replacement)
    column = func.lower(column)
    for search, replacement in _TURKISH_LOWER_REPLACEMENTS.items():
        column = func.replace(column, search, replacement)
    return column


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()
