# models.py (ilgili kısımları güncelle)
from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine, Integer, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.split("sqlite:///")[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(16), default="admin")  # admin/staff/user
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

def init_db():
    Base.metadata.create_all(bind=engine)
