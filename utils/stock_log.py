"""Utility helpers for working with stock logs."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import inspect, insert, select, func, text
from sqlalchemy.orm import Session

from models import StockLog, SessionLocal


_AVAILABLE_COLUMNS: set[str] | None = None
_CACHE_VERIFIED = False
_ISLEM_TRANSLATION = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"})
_ISLEM_ALIASES = {
    "girdi": "girdi",
    "cikti": "cikti",
    "cikis": "cikti",
    "hurda": "hurda",
    "atama": "atama",
}


def normalize_islem(value: Any, default: str = "girdi") -> tuple[str, bool]:
    """Normalize a movement type value to canonical form.

    Returns a tuple of ``(normalized, is_valid)``. ``is_valid`` indicates
    whether the provided value was recognised. When ``value`` is falsy the
    ``default`` is returned and considered valid.
    """

    if value is None:
        return default, True

    text = str(value).strip()
    if not text:
        return default, True

    lowered = text.lower().translate(_ISLEM_TRANSLATION)
    mapped = _ISLEM_ALIASES.get(lowered)
    if mapped:
        return mapped, True

    return default, False


def _load_available_columns() -> set[str]:
    global _AVAILABLE_COLUMNS
    if _AVAILABLE_COLUMNS is not None:
        return _AVAILABLE_COLUMNS

    session = None
    try:
        session = SessionLocal()
        bind = session.get_bind()
        if bind is None:
            _AVAILABLE_COLUMNS = {col.name for col in StockLog.__table__.columns}
        else:
            try:
                inspector = inspect(bind)
                columns = inspector.get_columns("stock_logs")
                if not columns:
                    raise RuntimeError("no columns")
                _AVAILABLE_COLUMNS = {col["name"] for col in columns}
            except Exception:  # pragma: no cover
                _AVAILABLE_COLUMNS = {col.name for col in StockLog.__table__.columns}
    except Exception:  # pragma: no cover - session init failure
        _AVAILABLE_COLUMNS = {col.name for col in StockLog.__table__.columns}
    finally:
        if session is not None:
            session.close()

    return _AVAILABLE_COLUMNS


def get_available_columns(db: Session | None = None) -> set[str]:
    """Return the set of physical columns for the ``stock_logs`` table.

    The helper preserves the module-level cache so expensive reflection is
    only performed once per process.  When a session is provided its bind is
    preferred for reflection, falling back to a new session (and ultimately
    to the model-defined columns) if necessary.
    """

    global _AVAILABLE_COLUMNS, _CACHE_VERIFIED

    if db is not None:
        runtime_columns: set[str] | None = None
        try:
            result = db.execute(text("SELECT * FROM stock_logs LIMIT 0"))
        except Exception:  # pragma: no cover - runtime lookup failures
            pass
        else:
            try:
                columns = tuple(result.keys())
                if columns:
                    runtime_columns = set(columns)
            finally:
                result.close()

        if runtime_columns:
            if _AVAILABLE_COLUMNS != runtime_columns:
                _AVAILABLE_COLUMNS = runtime_columns
            _CACHE_VERIFIED = True
            return _AVAILABLE_COLUMNS

    if _AVAILABLE_COLUMNS is not None and (_CACHE_VERIFIED or db is None):
        return _AVAILABLE_COLUMNS

    if db is not None:
        bind = db.get_bind()
        if bind is not None:
            try:
                inspector = inspect(bind)
                columns = inspector.get_columns("stock_logs")
            except Exception:  # pragma: no cover - reflection failures fallback
                columns = None
            else:
                if columns:
                    _AVAILABLE_COLUMNS = {col["name"] for col in columns}
                    _CACHE_VERIFIED = True
                    return _AVAILABLE_COLUMNS

            # Reflection failed or returned no columns; rely on the loader
            _AVAILABLE_COLUMNS = _load_available_columns()
            _CACHE_VERIFIED = True
            return _AVAILABLE_COLUMNS

    result = _load_available_columns()
    if db is None:
        _CACHE_VERIFIED = False
    return result


def create_stock_log(db: Session, *, return_id: bool = False, **fields: Any) -> int | None:
    """Insert a row into ``stock_logs`` while tolerating legacy schemas.

    Older deployments may not have all of the newer optional columns
    (``marka``, ``model``, ``source_type`` ...).  Writing through the ORM
    would fail in those environments because SQLAlchemy would still try to
    reference the missing columns.  This helper inspects the real table
    definition at runtime and only includes the columns that physically
    exist before issuing a manual INSERT statement.

    The function returns the inserted primary key when available so callers
    that need to expose it (e.g. API responses) can continue to do so.
    """

    available = get_available_columns(db)
    model_columns = {col.name for col in StockLog.__table__.columns}
    missing_columns = model_columns - available

    if not missing_columns:
        payload = {k: v for k, v in fields.items() if k in model_columns}
        if "tarih" not in payload:
            payload["tarih"] = datetime.utcnow()
        log = StockLog(**payload)
        db.add(log)
        if return_id:
            db.flush()
            return getattr(log, "id", None)
        return None

    data: dict[str, Any] = {}
    for key, value in fields.items():
        if key in available:
            data[key] = value

    if "tarih" in available and "tarih" not in data:
        data["tarih"] = datetime.utcnow()

    stmt = insert(StockLog.__table__).values(**data)
    result = db.execute(stmt)

    if not return_id:
        return None

    inserted_pk = getattr(result, "inserted_primary_key", None)
    if inserted_pk:
        return int(inserted_pk[0])

    if "id" in available:
        try:
            return int(result.scalar_one())  # type: ignore[arg-type]
        except Exception:  # pragma: no cover - fallback for drivers w/out RETURNING
            pk = db.execute(select(func.max(StockLog.id))).scalar()
            return int(pk) if pk is not None else None

    return None


# Preload available columns when module is imported to avoid reflection
# during transactional operations. Any failures simply fall back to the
# model-defined columns and will be re-evaluated lazily if needed.
try:  # pragma: no cover - defensive preload
    _load_available_columns()
except Exception:
    _AVAILABLE_COLUMNS = None
