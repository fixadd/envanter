from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password, pwd_context, verify_password
from models import User


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()
