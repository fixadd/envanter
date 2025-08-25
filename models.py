# models.py (ilgili kısımları güncelle)
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    create_engine,
    Integer,
    String,
    DateTime,
    Date,
    func,
    ForeignKey,
    Text,
    UniqueConstraint,
    inspect,
    text,
    JSON,
    Column,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
    relationship,
)

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
    bagli_envanter_no: Mapped[str | None] = mapped_column(String(150))
    kullanim_alani: Mapped[str | None] = mapped_column(String(150))
    ifs_no: Mapped[str | None] = mapped_column(String(150))
    durum: Mapped[str | None] = mapped_column(String(50), default="aktif")
    not_: Mapped[str | None] = mapped_column("not", Text)

    logs: Mapped[list["InventoryLog"]] = relationship(
        "InventoryLog", back_populates="inventory", cascade="all, delete-orphan"
    )

    licenses: Mapped[list["License"]] = relationship(
        "License",
        back_populates="inventory",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "no": self.no,
            "fabrika": self.fabrika,
            "departman": self.departman,
            "sorumlu_personel": self.sorumlu_personel,
            "bagli_envanter_no": self.bagli_envanter_no,
            "marka": self.marka,
            "model": self.model,
            "kullanim_alani": self.kullanim_alani,
            "ifs_no": self.ifs_no,
            "durum": self.durum,
            "not": self.not_,
        }


class InventoryLog(Base):
    __tablename__ = "inventory_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventories.id"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String, index=True)
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    note: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    inventory: Mapped["Inventory"] = relationship("Inventory", back_populates="logs")


class ScrapItem(Base):
    __tablename__ = "scrap_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_inventory_id: Mapped[int | None] = mapped_column(Integer, index=True)
    no: Mapped[str | None] = mapped_column(String, index=True)
    fabrika: Mapped[str | None] = mapped_column(String)
    departman: Mapped[str | None] = mapped_column(String)
    sorumlu_personel: Mapped[str | None] = mapped_column(String)
    marka: Mapped[str | None] = mapped_column(String)
    model: Mapped[str | None] = mapped_column(String)
    ifs_no: Mapped[str | None] = mapped_column(String)
    reason: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @classmethod
    def from_inventory(cls, inv: "Inventory", reason: str = "", actor: str = ""):
        return cls(
            source_inventory_id=inv.id,
            no=inv.no,
            fabrika=inv.fabrika,
            departman=inv.departman,
            sorumlu_personel=inv.sorumlu_personel,
            marka=inv.marka,
            model=inv.model,
            ifs_no=inv.ifs_no,
            reason=reason,
            actor=actor,
        )


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True)
    lisans_adi = Column(String(200), nullable=False)
    lisans_key = Column(String(500), nullable=True)
    sorumlu_personel = Column(String(120), nullable=True)
    bagli_envanter_no = Column(String(120), nullable=True)
    durum = Column(String(20), default="aktif")
    notlar = Column(Text, nullable=True)

    logs = relationship("LicenseLog", back_populates="license", cascade="all, delete-orphan")


class LicenseLog(Base):
    __tablename__ = "license_logs"
    id = Column(Integer, primary_key=True)
    license_id = Column(Integer, ForeignKey("licenses.id"), index=True, nullable=False)
    islem = Column(String(50))
    detay = Column(Text)
    islem_yapan = Column(String(120))
    tarih = Column(DateTime, default=datetime.utcnow)
    license = relationship("License", back_populates="logs")


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)

    models: Mapped[list["Model"]] = relationship(
        "Model", back_populates="brand", cascade="all, delete-orphan"
    )


class Model(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand_id: Mapped[int] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="models")
    __table_args__ = (UniqueConstraint("brand_id", "name", name="uq_brand_model"),)


class UsageArea(Base):
    __tablename__ = "usage_areas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)


class Factory(Base):
    __tablename__ = "factories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)


class LicenseName(Base):
    __tablename__ = "license_names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)


class HardwareType(Base):
    __tablename__ = "hardware_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)


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
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_id: Mapped[int | None] = mapped_column(
        ForeignKey("models.id", ondelete="SET NULL"), nullable=True, index=True
    )

    brand: Mapped[Brand | None] = relationship("Brand")
    model: Mapped[Model | None] = relationship("Model")

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
    """Create tables and perform lightweight migrations for SQLite."""

    insp = inspect(engine)

    # Legacy databases may contain an old `licenses` table with mismatched
    # columns (e.g. `lisans_adi`) from previous revisions. Accessing the
    # relationship on the ORM then results in a "no such column: licenses.adi"
    # error. If the expected `adi` column is missing we rename the existing
    # table so that a new one matching the current model can be created.
    if "licenses" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("licenses")}
        if "adi" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE licenses RENAME TO licenses_old"))

    # Create tables (including the possibly new `licenses` table)
    Base.metadata.create_all(bind=engine)

    # Ensure recently introduced nullable columns exist on older SQLite
    # databases. Missing fields trigger "no such column" errors when the ORM
    # attempts to access them. We inspect the schema and add any absent columns
    # using ``ALTER TABLE``; constraints and indexes are omitted for simplicity.

    # -- Licenses --------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("licenses")}
    with engine.begin() as conn:
        if "sorumlu_personel" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE licenses ADD COLUMN sorumlu_personel VARCHAR(150)"
                )
            )

    # -- Inventories -----------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("inventories")}
    with engine.begin() as conn:
        if "bagli_envanter_no" not in cols:
            if "bagli_makina_no" in cols:
                conn.execute(
                    text(
                        "ALTER TABLE inventories RENAME COLUMN bagli_makina_no TO bagli_envanter_no"
                    )
                )
            else:
                conn.execute(
                    text(
                        "ALTER TABLE inventories ADD COLUMN bagli_envanter_no VARCHAR(150)"
                    )
                )
        if "kullanim_alani" not in cols:
            conn.execute(
                text("ALTER TABLE inventories ADD COLUMN kullanim_alani VARCHAR(150)")
            )
        if "durum" not in cols:
            conn.execute(
                text("ALTER TABLE inventories ADD COLUMN durum VARCHAR(50) DEFAULT 'aktif'")
            )
        if "ifs_no" not in cols:
            conn.execute(
                text("ALTER TABLE inventories ADD COLUMN ifs_no VARCHAR(150)")
            )

    # -- Printers --------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("printers")}
    with engine.begin() as conn:
        if "brand_id" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN brand_id INTEGER"))
        if "model_id" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN model_id INTEGER"))
