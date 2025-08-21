# models.py (ilgili kısımları güncelle)
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Integer,
    String,
    DateTime,
    func,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship

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


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    no: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    fabrika: Mapped[str | None] = mapped_column(String(150), index=True)
    departman: Mapped[str | None] = mapped_column(String(150), index=True)
    donanim_tipi: Mapped[str | None] = mapped_column(String(100), index=True)
    bilgisayar_adi: Mapped[str | None] = mapped_column(String(150), index=True)
    marka: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    seri_no: Mapped[str | None] = mapped_column(String(150))
    sorumlu_personel: Mapped[str | None] = mapped_column(String(150), index=True)
    bagli_makina_no: Mapped[str | None] = mapped_column(String(150))
    ifs_no: Mapped[str | None] = mapped_column(String(150))
    tarih: Mapped[str | None] = mapped_column(String(50))
    islem_yapan: Mapped[str | None] = mapped_column(String(150))
    notlar: Mapped[str | None] = mapped_column("not", Text)

    logs: Mapped[list["InventoryLog"]] = relationship(
        "InventoryLog", back_populates="inventory", cascade="all, delete-orphan"
    )


class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("inventories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(150), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    inventory: Mapped["Inventory"] = relationship("Inventory", back_populates="logs")


class License(Base):
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lisans_adi: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    lisans_anahtari: Mapped[str] = mapped_column(String(500), nullable=False)
    sorumlu_personel: Mapped[str | None] = mapped_column(String(150), index=True)
    bagli_envanter_no: Mapped[str | None] = mapped_column(String(150), index=True)
    ifs_no: Mapped[str | None] = mapped_column(String(150))
    tarih: Mapped[str | None] = mapped_column(String(50))
    islem_yapan: Mapped[str | None] = mapped_column(String(150))
    mail_adresi: Mapped[str | None] = mapped_column(String(200))

    logs: Mapped[list["LicenseLog"]] = relationship(
        "LicenseLog", back_populates="license_", cascade="all, delete-orphan"
    )


class LicenseLog(Base):
    __tablename__ = "license_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    license_id: Mapped[int] = mapped_column(
        ForeignKey("licenses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(150), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    license_: Mapped["License"] = relationship("License", back_populates="logs")


class Printer(Base):
    __tablename__ = "printers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    envanter_no: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    yazici_markasi: Mapped[str | None] = mapped_column(String(150), index=True)
    yazici_modeli: Mapped[str | None] = mapped_column(String(150), index=True)
    kullanim_alani: Mapped[str | None] = mapped_column(String(200), index=True)
    ip_adresi: Mapped[str | None] = mapped_column(String(100), index=True)
    mac: Mapped[str | None] = mapped_column(String(100), index=True)
    hostname: Mapped[str | None] = mapped_column(String(150), index=True)
    ifs_no: Mapped[str | None] = mapped_column(String(150))
    tarih: Mapped[str | None] = mapped_column(String(50))
    islem_yapan: Mapped[str | None] = mapped_column(String(150))
    sorumlu_personel: Mapped[str | None] = mapped_column(String(150), index=True)

    logs: Mapped[list["PrinterLog"]] = relationship(
        "PrinterLog", back_populates="printer", cascade="all, delete-orphan"
    )


class PrinterLog(Base):
    __tablename__ = "printer_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    printer_id: Mapped[int] = mapped_column(
        ForeignKey("printers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(150), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    printer: Mapped["Printer"] = relationship("Printer", back_populates="logs")


class Lookup(Base):
    __tablename__ = "lookups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    value: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("category", "value", name="uq_lookup_category_value"),)


def init_db():
    Base.metadata.create_all(bind=engine)
