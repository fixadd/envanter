# models.py (ilgili kısımları güncelle)
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, date
from typing import Optional
import enum
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
    Enum,
)
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
    relationship,
    synonym,
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.split("sqlite:///")[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(60), default="")
    last_name: Mapped[str] = mapped_column(String(60), default="")
    full_name: Mapped[str] = mapped_column(String(120), default="")
    # E-posta artık opsiyonel ve benzersiz
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(16), default="admin")  # admin/staff/user
    theme: Mapped[str] = mapped_column(String(20), default="default")
    animation: Mapped[str] = mapped_column(String(20), default="none")
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Connection(Base):
    __tablename__ = "connections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=389)
    base_dn: Mapped[str] = mapped_column(String(255))
    user_dn: Mapped[str] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    no: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
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
    tarih: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    islem_yapan: Mapped[str | None] = mapped_column(String(150))
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
            "tarih": self.tarih,
            "islem_yapan": self.islem_yapan,
            "durum": self.durum,
            "not": self.not_,
        }


class InventoryLog(Base):
    __tablename__ = "inventory_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("inventories.id"), index=True, nullable=False
    )
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
    lisans_adi = Column(String(200), nullable=True)
    lisans_anahtari = Column(String(500), nullable=True)
    lisans_key = synonym("lisans_anahtari")
    anahtar = synonym("lisans_anahtari")
    sorumlu_personel = Column(String(120), nullable=True)
    bagli_envanter_no = Column(String(120), nullable=True)
    ifs_no = Column(String(100), nullable=True)
    tarih = Column(Date, default=datetime.utcnow)
    islem_yapan = Column(String(120), nullable=True)
    mail_adresi = Column(String(200), nullable=True)
    inventory_id = Column(
        Integer,
        ForeignKey("inventories.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    durum = Column(String(20), default="aktif")
    notlar = Column(Text, nullable=True)

    logs = relationship(
        "LicenseLog", back_populates="license", cascade="all, delete-orphan"
    )
    inventory = relationship("Inventory", back_populates="licenses")


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
    name: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )

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
    name: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )


class Factory(Base):
    __tablename__ = "factories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )


class LicenseName(Base):
    __tablename__ = "license_names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True
    )


class HardwareType(Base):
    __tablename__ = "hardware_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )


class Printer(Base):
    __tablename__ = "printers"

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, index=True)
    marka = Column(String(100))
    model = Column(String(100))
    seri_no = Column(String(100))

    fabrika = Column(String(100), nullable=True)
    kullanim_alani = Column(String(150), nullable=True)
    sorumlu_personel = Column(String(150), nullable=True)
    bagli_envanter_no = Column(String(50), nullable=True)
    envanter_no = Column(String(100), nullable=True)
    ip_adresi = Column(String(50), nullable=True)
    mac = Column(String(50), nullable=True)
    hostname = Column(String(100), nullable=True)
    ifs_no = Column(String(100), nullable=True)
    tarih = Column(Date, default=datetime.utcnow)
    islem_yapan = Column(String(150), nullable=True)

    durum = Column(String(30), default="aktif")
    notlar = Column(Text, nullable=True)

    histories = relationship(
        "PrinterHistory", back_populates="printer", cascade="all, delete-orphan"
    )


class PrinterHistory(Base):
    __tablename__ = "printer_histories"

    id = Column(Integer, primary_key=True)
    printer_id = Column(Integer, ForeignKey("printers.id"), index=True)
    action = Column(String(50))
    changes = Column(SQLITE_JSON, nullable=True)
    actor = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    printer = relationship("Printer", back_populates="histories")


class ScrapPrinter(Base):
    __tablename__ = "scrap_printers"

    id = Column(Integer, primary_key=True)
    printer_id = Column(Integer, index=True, unique=True)
    snapshot = Column(SQLITE_JSON)
    reason = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StockLog(Base):
    __tablename__ = "stock_logs"
    id = Column(Integer, primary_key=True, index=True)
    donanim_tipi = Column(String(150), index=True, nullable=False)
    miktar = Column(Integer, nullable=False)
    ifs_no = Column(String(100), index=True, nullable=True)
    marka = Column(String(150), nullable=True)
    model = Column(String(150), nullable=True)
    lisans_anahtari = Column(String(500), nullable=True)
    mail_adresi = Column(String(200), nullable=True)
    tarih = Column(DateTime, default=datetime.utcnow)
    islem = Column(
        Enum("girdi", "cikti", "hurda", "atama", name="stock_islem"), nullable=False
    )
    actor = Column(String(150), nullable=True)


class StockAssignment(Base):
    __tablename__ = "stock_assignments"
    id = Column(Integer, primary_key=True)
    donanim_tipi = Column(String(150), nullable=False)
    miktar = Column(Integer, nullable=False)
    ifs_no = Column(String(100), nullable=True)
    hedef_envanter_no = Column(String(100), nullable=True)
    sorumlu_personel = Column(String(150), nullable=True)
    kullanim_alani = Column(String(150), nullable=True)
    tarih = Column(DateTime, default=datetime.utcnow)
    actor = Column(String(150), nullable=True)


class StockTotal(Base):
    __tablename__ = "stock_totals"
    donanim_tipi = Column(String(150), primary_key=True)
    toplam = Column(Integer, nullable=False, default=0)


class TalepDurum(str, enum.Enum):
    AKTIF = "aktif"
    TAMAMLANDI = "tamamlandi"
    IPTAL = "iptal"

    def __str__(self) -> str:
        return str(self.value)


class TalepTuru(str, enum.Enum):
    ENVANTER = "envanter"
    LISANS = "lisans"
    AKSESUAR = "aksesuar"

    def __str__(self) -> str:
        return str(self.value)


class Talep(Base):
    __tablename__ = "talepler"

    id = Column(Integer, primary_key=True, index=True)
    tur = Column(Enum(TalepTuru), nullable=False)
    donanim_tipi = Column(String(150), nullable=True)

    ifs_no = Column(String(100), index=True, nullable=True)
    miktar = Column(Integer, nullable=True)
    marka = Column(String(150), nullable=True)
    model = Column(String(150), nullable=True)

    envanter_no = Column(String(100), nullable=True)
    sorumlu_personel = Column(String(150), nullable=True)
    bagli_envanter_no = Column(String(100), nullable=True)
    lisans_adi = Column(String(200), nullable=True)

    aciklama = Column(Text, nullable=True)
    durum = Column(Enum(TalepDurum), default=TalepDurum.AKTIF, nullable=False)
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow, nullable=False)
    kapanma_tarihi = Column(DateTime, nullable=True)


class Lookup(Base):
    __tablename__ = "lookups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    value: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("type", "value", name="uq_lookup_type_value"),)


def init_db():
    """Create tables and perform lightweight migrations for SQLite."""

    # Create all tables if they do not exist
    Base.metadata.create_all(bind=engine)

    # Ensure recently introduced columns exist on older SQLite databases.
    # Missing fields trigger "no such column" errors when the ORM attempts to
    # access them. We inspect the schema and add or rename columns as needed.

    # -- Users ---------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("users")}
    with engine.begin() as conn:
        if "first_name" not in cols:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN first_name VARCHAR(60) DEFAULT ''")
            )
        if "last_name" not in cols:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN last_name VARCHAR(60) DEFAULT ''")
            )
        if "full_name" not in cols:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN full_name VARCHAR(120) DEFAULT ''")
            )
        if "email" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))
        if "role" not in cols:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(16) DEFAULT 'admin'")
            )
        if "theme" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN theme VARCHAR(20) DEFAULT 'default'"
                )
            )
        if "animation" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN animation VARCHAR(20) DEFAULT 'none'"
                )
            )
        if "created_at" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                )
            )

    # -- Lookups -------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("lookups")}
    with engine.begin() as conn:
        if "type" not in cols and "category" in cols:
            conn.execute(text("ALTER TABLE lookups RENAME COLUMN category TO type"))

    # -- Licenses --------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("licenses")}
    with engine.begin() as conn:
        if "lisans_adi" not in cols:
            if "adi" in cols:
                conn.execute(
                    text("ALTER TABLE licenses RENAME COLUMN adi TO lisans_adi")
                )
            else:
                conn.execute(
                    text("ALTER TABLE licenses ADD COLUMN lisans_adi VARCHAR(200)")
                )
        if "lisans_anahtari" not in cols:
            if "anahtari" in cols:
                conn.execute(
                    text(
                        "ALTER TABLE licenses RENAME COLUMN anahtari TO lisans_anahtari"
                    )
                )
            else:
                conn.execute(
                    text("ALTER TABLE licenses ADD COLUMN lisans_anahtari VARCHAR(500)")
                )
        if "sorumlu_personel" not in cols:
            conn.execute(
                text("ALTER TABLE licenses ADD COLUMN sorumlu_personel VARCHAR(150)")
            )
        if "bagli_envanter_no" not in cols:
            conn.execute(
                text("ALTER TABLE licenses ADD COLUMN bagli_envanter_no VARCHAR(150)")
            )
        if "inventory_id" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN inventory_id INTEGER"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_licenses_inventory_id ON licenses(inventory_id)"
                )
            )
        if "durum" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE licenses ADD COLUMN durum VARCHAR(20) DEFAULT 'aktif'"
                )
            )
        if "notlar" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN notlar TEXT"))
        if "ifs_no" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN ifs_no VARCHAR(100)"))
        if "tarih" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN tarih DATE"))
        if "islem_yapan" not in cols:
            conn.execute(
                text("ALTER TABLE licenses ADD COLUMN islem_yapan VARCHAR(120)")
            )
        if "mail_adresi" not in cols:
            conn.execute(
                text("ALTER TABLE licenses ADD COLUMN mail_adresi VARCHAR(200)")
            )

    # -- License Logs ----------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("license_logs")}
    with engine.begin() as conn:
        if "islem" not in cols:
            if "field" in cols:
                conn.execute(
                    text("ALTER TABLE license_logs RENAME COLUMN field TO islem")
                )
            else:
                conn.execute(
                    text("ALTER TABLE license_logs ADD COLUMN islem VARCHAR(50)")
                )
        if "detay" not in cols:
            if "old_value" in cols:
                conn.execute(
                    text("ALTER TABLE license_logs RENAME COLUMN old_value TO detay")
                )
            else:
                conn.execute(text("ALTER TABLE license_logs ADD COLUMN detay TEXT"))
        if "islem_yapan" not in cols:
            if "changed_by" in cols:
                conn.execute(
                    text(
                        "ALTER TABLE license_logs RENAME COLUMN changed_by TO islem_yapan"
                    )
                )
            else:
                conn.execute(
                    text("ALTER TABLE license_logs ADD COLUMN islem_yapan VARCHAR(120)")
                )
        if "tarih" not in cols:
            if "changed_at" in cols:
                conn.execute(
                    text("ALTER TABLE license_logs RENAME COLUMN changed_at TO tarih")
                )
            else:
                conn.execute(text("ALTER TABLE license_logs ADD COLUMN tarih DATETIME"))

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
                text(
                    "ALTER TABLE inventories ADD COLUMN durum VARCHAR(50) DEFAULT 'aktif'"
                )
            )
        if "ifs_no" not in cols:
            conn.execute(text("ALTER TABLE inventories ADD COLUMN ifs_no VARCHAR(150)"))

    # -- Talepler --------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("talepler")}
    with engine.begin() as conn:
        if "donanim_tipi" not in cols:
            conn.execute(
                text("ALTER TABLE talepler ADD COLUMN donanim_tipi VARCHAR(150)")
            )
        if "kapanma_tarihi" not in cols:
            conn.execute(
                text("ALTER TABLE talepler ADD COLUMN kapanma_tarihi DATETIME")
            )

    # -- Printers --------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("printers")}
    with engine.begin() as conn:
        if "inventory_id" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN inventory_id INTEGER"))
        if "marka" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN marka VARCHAR(100)"))
        if "model" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN model VARCHAR(100)"))
        if "seri_no" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN seri_no VARCHAR(100)"))
        if "fabrika" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN fabrika VARCHAR(100)"))
        if "kullanim_alani" not in cols:
            conn.execute(
                text("ALTER TABLE printers ADD COLUMN kullanim_alani VARCHAR(150)")
            )
        if "sorumlu_personel" not in cols:
            conn.execute(
                text("ALTER TABLE printers ADD COLUMN sorumlu_personel VARCHAR(150)")
            )
        if "bagli_envanter_no" not in cols:
            conn.execute(
                text("ALTER TABLE printers ADD COLUMN bagli_envanter_no VARCHAR(50)")
            )
        if "durum" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE printers ADD COLUMN durum VARCHAR(30) DEFAULT 'aktif'"
                )
            )
        if "notlar" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN notlar TEXT"))
        if "envanter_no" not in cols:
            conn.execute(
                text("ALTER TABLE printers ADD COLUMN envanter_no VARCHAR(100)")
            )
        if "ip_adresi" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN ip_adresi VARCHAR(50)"))
        if "mac" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN mac VARCHAR(50)"))
        if "hostname" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN hostname VARCHAR(100)"))
        if "ifs_no" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN ifs_no VARCHAR(100)"))
        if "tarih" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN tarih DATE"))
        if "islem_yapan" not in cols:
            conn.execute(
                text("ALTER TABLE printers ADD COLUMN islem_yapan VARCHAR(150)")
            )

    # -- Stock Logs --------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("stock_logs")}
    with engine.begin() as conn:
        if "ifs_no" not in cols:
            conn.execute(text("ALTER TABLE stock_logs ADD COLUMN ifs_no VARCHAR(100)"))
        if "marka" not in cols:
            conn.execute(text("ALTER TABLE stock_logs ADD COLUMN marka VARCHAR(150)"))
        if "model" not in cols:
            conn.execute(text("ALTER TABLE stock_logs ADD COLUMN model VARCHAR(150)"))
        if "lisans_anahtari" not in cols:
            conn.execute(
                text("ALTER TABLE stock_logs ADD COLUMN lisans_anahtari VARCHAR(500)")
            )
        if "mail_adresi" not in cols:
            conn.execute(
                text("ALTER TABLE stock_logs ADD COLUMN mail_adresi VARCHAR(200)")
            )
        if "actor" not in cols:
            conn.execute(text("ALTER TABLE stock_logs ADD COLUMN actor VARCHAR(150)"))
