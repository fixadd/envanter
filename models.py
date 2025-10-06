# models.py (ilgili kısımları güncelle)
from __future__ import annotations

import enum
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
    synonym,
)
from sqlalchemy.pool import StaticPool

load_dotenv()


def _resolve_database_url() -> str:
    """Return the configured database URL with legacy fallbacks."""

    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    legacy_paths = [
        Path("./data/envanter.db"),
        Path("./data/envanter.sqlite"),
        Path("./data/envanter.sqlite3"),
    ]

    for path in legacy_paths:
        if path.exists():
            return f"sqlite:///{path.as_posix()}"

    return "sqlite:///./data/app.db"


DATABASE_URL = _resolve_database_url()


def _is_sqlite_url(url: str | URL) -> bool:
    parsed = url if isinstance(url, URL) else make_url(url)
    return parsed.get_backend_name() == "sqlite"


def engine_kwargs_for_url(url: str | URL) -> dict[str, Any]:
    """Return safe keyword arguments for :func:`create_engine`.

    The helper normalises SQLite URLs so that tests can override the
    ``poolclass`` (e.g. to use :class:`StaticPool`) without running into the
    ``multiple values for keyword argument`` error that SQLAlchemy raises when
    the same kwarg is passed twice. To keep backwards compatibility for the
    application code we expose the pool selection via a separate helper.
    """

    if _is_sqlite_url(url):
        return {"connect_args": {"check_same_thread": False}}
    return {}


def engine_pool_kwargs(url: str | URL) -> dict[str, Any]:
    """Return optional pool-related kwargs for SQLite memory databases."""

    if not _is_sqlite_url(url):
        return {}
    parsed = url if isinstance(url, URL) else make_url(url)
    if parsed.database in (None, "", ":memory:"):
        return {"poolclass": StaticPool}
    return {}


database_url = make_url(DATABASE_URL)
if _is_sqlite_url(database_url):
    db_path = database_url.database
    if db_path and db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

_engine_kwargs = engine_kwargs_for_url(database_url)
_engine_kwargs.update(engine_pool_kwargs(database_url))
engine = create_engine(DATABASE_URL, **_engine_kwargs)
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

    pin_limit: Mapped[Optional["UserPinLimit"]] = relationship(
        "UserPinLimit",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
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


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    donanim_tipi: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    marka: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    kullanim_alani: Mapped[str | None] = mapped_column(
        String(150), nullable=True, index=True
    )
    lisans_adi: Mapped[str | None] = mapped_column(String(150), nullable=True)
    fabrika: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)


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
    license_key = synonym("lisans_anahtari")
    product_name = synonym("lisans_adi")
    sorumlu_personel = Column(String(120), nullable=True)
    bagli_envanter_no = Column(String(120), nullable=True)
    ifs_no = Column(String(100), nullable=True)
    tarih = Column(Date, default=datetime.utcnow)
    islem_yapan = Column(String(120), nullable=True)
    mail_adresi = Column(String(200), nullable=True)
    license_code = Column(String(64), unique=True, index=True, nullable=True)
    license_type = Column(String(32), nullable=True)
    seat_count = Column(Integer, nullable=False, default=1)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    factory_id = Column(
        Integer, ForeignKey("factories.id", ondelete="SET NULL"), nullable=True
    )
    department_id = Column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    inventory_id = Column(
        Integer,
        ForeignKey("inventories.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    durum = Column(String(20), default="aktif")
    notlar = Column(Text, nullable=True)
    note = synonym("notlar")

    logs = relationship(
        "LicenseLog", back_populates="license", cascade="all, delete-orphan"
    )
    inventory = relationship("Inventory", back_populates="licenses")
    factory = relationship("Factory", foreign_keys=[factory_id])
    department = relationship("Department", foreign_keys=[department_id])
    owner = relationship("User", foreign_keys=[owner_id])


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


class Department(Base):
    __tablename__ = "departments"

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


class FaultRecord(Base):
    __tablename__ = "fault_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    entity_key = Column(String(200), nullable=True, index=True)
    title = Column(String(200), nullable=True)
    device_no = Column(String(120), nullable=True)
    reason = Column(Text, nullable=True)
    destination = Column(String(200), nullable=True)
    status = Column(String(30), nullable=False, default="arızalı", index=True)
    created_by = Column(String(120), nullable=True)
    resolved_by = Column(String(120), nullable=True)
    note = Column(Text, nullable=True)
    meta = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_key": self.entity_key,
            "title": self.title,
            "device_no": self.device_no,
            "reason": self.reason,
            "destination": self.destination,
            "status": self.status,
            "created_by": self.created_by,
            "resolved_by": self.resolved_by,
            "note": self.note,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
        }
        if self.meta:
            try:
                data["meta"] = json.loads(self.meta)
            except json.JSONDecodeError:
                data["meta"] = self.meta
        else:
            data["meta"] = None
        return data


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
    aciklama = Column(Text, nullable=True)
    tarih = Column(DateTime, default=datetime.utcnow)
    islem = Column(
        Enum("girdi", "cikti", "hurda", "atama", name="stock_islem"), nullable=False
    )
    actor = Column(String(150), nullable=True)
    # new fields to track where stock movements originate from
    source_type = Column(String(50), nullable=True)
    source_id = Column(Integer, nullable=True)


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


class SystemRoomItem(Base):
    __tablename__ = "system_room_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type = Column(String(20), nullable=False)
    donanim_tipi = Column(String(150), nullable=False)
    marka = Column(String(150), nullable=True)
    model = Column(String(150), nullable=True)
    ifs_no = Column(String(100), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_by = Column(String(150), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "item_type",
            "donanim_tipi",
            "marka",
            "model",
            "ifs_no",
            name="uq_system_room_key",
        ),
    )


class StockTotal(Base):
    __tablename__ = "stock_totals"
    donanim_tipi = Column(String(150), primary_key=True)
    toplam = Column(Integer, nullable=False, default=0)


class TalepDurum(str, enum.Enum):
    ACIK = "acik"
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
    miktar = Column(Integer, nullable=False)
    karsilanan_miktar = Column(Integer, default=0, nullable=False)
    kalan_miktar = Column(Integer, default=0, nullable=False)
    marka = Column(String(150), nullable=True)
    model = Column(String(150), nullable=True)

    envanter_no = Column(String(100), nullable=True)
    sorumlu_personel = Column(String(150), nullable=True)
    bagli_envanter_no = Column(String(100), nullable=True)
    lisans_adi = Column(String(200), nullable=True)

    aciklama = Column(Text, nullable=True)
    durum = Column(Enum(TalepDurum), default=TalepDurum.ACIK, nullable=False)
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


class BilgiKategori(Base):
    __tablename__ = "bilgi_kategorileri"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ad: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    aciklama: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    bilgiler: Mapped[list["Bilgi"]] = relationship(
        "Bilgi", back_populates="kategori", cascade="all, delete-orphan"
    )


class Bilgi(Base):
    __tablename__ = "bilgiler"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    kategori_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("bilgi_kategorileri.id"), nullable=True, index=True
    )
    icerik: Mapped[str] = mapped_column(Text, nullable=False)
    foto_yolu: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kullanici_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pinned_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    kategori: Mapped[Optional["BilgiKategori"]] = relationship(
        "BilgiKategori", back_populates="bilgiler"
    )
    author: Mapped["User"] = relationship("User", foreign_keys=[kullanici_id])
    pinned_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[pinned_by], viewonly=True
    )


class UserPinLimit(Base):
    __tablename__ = "user_pin_limits"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), primary_key=True, nullable=False
    )
    pin_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="pin_limit")


def init_db() -> None:
    """Backwards compatible wrapper for :mod:`app.db.init`."""

    from app.db.init import init_db as _init_db

    _init_db()
