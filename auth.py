from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password, pwd_context, verify_password
from models import User


def get_user_by_username(db: Session, username: str) -> User | None:
    normalized = (username or "").strip()
    if not normalized:
        return None

    return (
        db.query(User)
        .filter(func.lower(User.username) == normalized.lower())
        .first()
    )


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()
