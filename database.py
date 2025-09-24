from __future__ import annotations

from sqlalchemy.orm import Session

from models import SessionLocal


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
