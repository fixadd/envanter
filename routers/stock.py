from datetime import datetime
from typing import Literal, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Brand,
    HardwareType,
    Inventory,
    InventoryLog,
    License,
    LicenseLog,
    LicenseName,
    Model,
    Printer,
    PrinterHistory,
    StockAssignment,
    StockLog,
    StockTotal,
    SystemRoomItem,
    UsageArea,
)
from routers.api import stock_status_detail
from security import current_user
from utils.stock_log import create_stock_log, normalize_islem

router = APIRouter(prefix="/stock", tags=["Stock"])
api_router = APIRouter(prefix="/api/stock", tags=["stock"])
templates = Jinja2Templates(directory="templates")


@router.get("/export")
async def export_stock(db: Session = Depends(get_db)):
    """Export current stock status (with summary) as an Excel file."""
    from io import BytesIO

    from openpyxl import Workbook

    items = stock_status(db)
    detail = stock_status_detail(db)
    totals = detail.get("totals") or {}

    wb = Workbook()
    ws = wb.active
    ws.title = "Stok Durumu"

    ws.append(
        [
            "Donanım Tipi",
            "Marka",
            "Model",
            "IFS No",
            "Stok",
            "Son İşlem",
            "Kaynak Türü",
            "Kaynak ID",
        ]
    )

    def format_ts(value):
        if isinstance(value, datetime):
            return value.strftime("%d.%m.%Y %H:%M")
        return value or ""

    source_labels = {
        "envanter": "Envanter",
        "lisans": "Lisans",
        "yazici": "Yazıcı",
    }

    sorted_items = sorted(
        items,
        key=lambda row: (
            row.get("donanim_tipi") or "",
            row.get("marka") or "",
            row.get("model") or "",
            row.get("ifs_no") or "",
        ),
    )

    for row in sorted_items:
        raw_source = row.get("source_type") or ""
        source_lower = str(raw_source).lower()
        if ":" in source_lower:
            _, base = source_lower.split(":", 1)
        else:
            base = source_lower
        base_label = source_labels.get(base, base.title() if base else "")
        if source_lower.startswith("talep:"):
            source_label = f"Talep ({base_label})" if base_label else "Talep"
        else:
            source_label = source_labels.get(source_lower, raw_source)
        ws.append(
            [
                row.get("donanim_tipi") or "",
                row.get("marka") or "",
                row.get("model") or "",
                row.get("ifs_no") or "",
                row.get("net_miktar") or 0,
                format_ts(row.get("son_islem_ts")),
                source_label,
                row.get("source_id") or "",
            ]
        )

    if not sorted_items:
        ws.append(["-", "-", "-", "-", 0, "-", "", ""])

    summary_data: dict[str, int] = {}
    for row in items:
        key = row.get("donanim_tipi") or "-"
        summary_data[key] = summary_data.get(key, 0) + int(row.get("net_miktar") or 0)

    if not summary_data and totals:
        summary_data = {str(k): int(v) for k, v in totals.items()}

    if summary_data:
        summary_ws = wb.create_sheet(title="Özet")
        summary_ws.append(["Donanım Tipi", "Toplam Stok"])
        for name, value in sorted(summary_data.items()):
            summary_ws.append([name, value])

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    headers = {"Content-Disposition": "attachment; filename=stock_status.xlsx"}
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/import", response_class=PlainTextResponse)
async def import_stock(file: UploadFile = File(...)):
    return f"Received {file.filename}, but import is not implemented."


def _stock_lookups(db: Session) -> dict[str, list[str]]:
    donanim_tipi = [
        row.name
        for row in db.query(HardwareType).order_by(HardwareType.name.asc()).all()
        if (row.name or "").strip()
    ]
    marka = [row.name for row in db.query(Brand).order_by(Brand.name.asc()).all()]
    return {"donanim_tipi": donanim_tipi, "marka": marka}


@router.get("", response_class=HTMLResponse)
def stock_list(request: Request, db: Session = Depends(get_db)):
    logs = db.query(StockLog).order_by(StockLog.tarih.desc(), StockLog.id.desc()).all()
    lookups = _stock_lookups(db)
    current_id = request.query_params.get("id") or request.query_params.get("item")
    try:
        current_id_int = int(current_id) if current_id else None
    except (TypeError, ValueError):
        current_id_int = None
    current_item = db.get(StockLog, current_id_int) if current_id_int else None
    return templates.TemplateResponse(
        "stock/index.html",
        {
            "request": request,
            "logs": logs,
            "lookups": lookups,
            "current_id": current_id_int,
            "current_item": current_item,
        },
    )


@router.get("/durum", response_class=HTMLResponse)
def stock_status_page(request: Request):
    """Stok durumunu HTML olarak göster."""
    return templates.TemplateResponse("stock.html", {"request": request})


@router.get("/durum/json")
def stock_status_json(db: Session = Depends(get_db)):
    """Stok durumunu JSON olarak döndür."""
    detail = stock_status_detail(db)
    items = stock_status(db)
    return {"ok": True, "totals": detail["totals"], "items": items}


@api_router.get("/status")
def stock_status(db: Session = Depends(get_db)):
    """Stok durumunu detaylı biçimde döndür.

    Her satır donanım tipi, marka, model ve opsiyonel IFS numarasına göre
    gruplanmış net miktarı içerir. ``net_miktar`` değeri tüm "girdi"
    işlemlerinin toplamından "cikti", "hurda" ve "atama" işlemlerinin
    toplamının çıkarılmasıyla hesaplanır. Son işlem zaman damgası
    ``son_islem_ts`` alanında döner.
    """

    status = stock_status_detail(db)
    hardware_map = {str(h.id): h.name for h in db.query(HardwareType).all()}
    license_map = {
        str(license_name.id): license_name.name
        for license_name in db.query(LicenseName).all()
    }
    brand_map = {str(b.id): b.name for b in db.query(Brand).all()}
    model_map = {str(m.id): m.name for m in db.query(Model).all()}

    items = []
    for r in status["items"]:
        donanim = r["donanim_tipi"]
        if donanim in hardware_map:
            donanim = hardware_map[donanim]
        elif donanim in license_map:
            donanim = license_map[donanim]

        marka = r.get("marka") or None
        if marka and marka in brand_map:
            marka = brand_map[marka]

        model = r.get("model") or None
        if model and model in model_map:
            model = model_map[model]

        items.append(
            {
                "donanim_tipi": donanim,
                "marka": marka,
                "model": model,
                "ifs_no": r.get("ifs_no") or "",
                "net_miktar": r.get("net"),
                "son_islem_ts": r.get("last_tarih"),
                "source_type": r.get("source_type"),
                "source_id": r.get("source_id"),
                "item_type": r.get("item_type"),
                "assignment_hint": r.get("assignment_hint"),
                "system_room": bool(r.get("system_room")),
                "system_room_assigned_at": r.get("system_room_assigned_at"),
                "system_room_assigned_by": r.get("system_room_assigned_by"),
            }
        )
    return items


@router.post("/add")
def stock_add(payload: dict = Body(...), db: Session = Depends(get_db)):
    # UI yeni adla `is_lisans` gönderiyor; eski `is_license` ile de uyumlu
    # kalmak için her ikisini de kontrol ediyoruz.
    is_license = payload.get("is_lisans") or payload.get("is_license")

    # Donanım tipi zorunlu; boş veya None gelirse 500 yerine anlamlı hata döndür.
    donanim_tipi_raw = payload.get("donanim_tipi")
    if donanim_tipi_raw is None:
        donanim_tipi_raw = ""
    donanim_tipi = str(donanim_tipi_raw).strip()

    if donanim_tipi and donanim_tipi.isdigit():
        ht = db.get(HardwareType, int(donanim_tipi))
        if ht:
            donanim_tipi = ht.name
        else:
            ln = db.get(LicenseName, int(donanim_tipi))
            if ln:
                donanim_tipi = ln.name

    if not donanim_tipi:
        return {"ok": False, "error": "Donanım tipi seçiniz"}

    marka = None if is_license else payload.get("marka")
    if marka and marka.isdigit():
        b = db.get(Brand, int(marka))
        if b:
            marka = b.name

    model = None if is_license else payload.get("model")
    if model and model.isdigit():
        m = db.get(Model, int(model))
        if m:
            model = m.name

    if is_license:
        miktar = 1
    else:
        try:
            miktar = int(payload.get("miktar"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "Miktar 0'dan büyük olmalı"}
        if miktar <= 0:
            return {"ok": False, "error": "Miktar 0'dan büyük olmalı"}
    islem_raw = payload.get("islem")
    islem, islem_valid = normalize_islem(islem_raw)
    if islem_raw and not islem_valid:
        return {"ok": False, "error": "Geçersiz işlem türü"}

    total = db.get(StockTotal, donanim_tipi) or StockTotal(
        donanim_tipi=donanim_tipi, toplam=0
    )
    if islem in ("cikti", "hurda", "atama") and total.toplam < miktar:
        return {"ok": False, "error": "Yetersiz stok"}

    log_id = create_stock_log(
        db,
        return_id=True,
        donanim_tipi=donanim_tipi,
        marka=marka,
        model=model,
        lisans_anahtari=payload.get("lisans_anahtari") if is_license else None,
        mail_adresi=payload.get("mail_adresi") if is_license else None,
        miktar=miktar,
        ifs_no=payload.get("ifs_no") or None,
        aciklama=payload.get("aciklama"),
        islem=islem,
        tarih=datetime.utcnow(),
        actor=payload.get("islem_yapan") or "Sistem",
        source_type=payload.get("source_type"),
        source_id=payload.get("source_id"),
    )

    if islem == "girdi":
        total.toplam += miktar
    else:
        total.toplam -= miktar
    db.merge(total)
    db.commit()
    return {"ok": True, "id": log_id or 0}


class StockOption(BaseModel):
    """UI'daki stok seçenekleri için DTO."""

    id: str
    label: str
    donanim_tipi: Optional[str] = None
    marka: Optional[str] = None
    model: Optional[str] = None
    ifs_no: Optional[str] = None
    lisans_anahtari: Optional[str] = None
    mail_adresi: Optional[str] = None
    mevcut_miktar: int
    source_type: Optional[str] = None
    source_id: Optional[int] = None


class SystemRoomItemKey(BaseModel):
    item_type: Literal["envanter", "lisans", "yazici"]
    donanim_tipi: str
    marka: Optional[str] = None
    model: Optional[str] = None
    ifs_no: Optional[str] = None

    @validator("item_type", pre=True)
    def _normalize_type(cls, value: str) -> str:
        if value is None:
            return "envanter"
        return str(value).strip().lower()

    @validator("donanim_tipi")
    def _validate_donanim(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("donanım tipi boş olamaz")
        return text

    @validator("marka", "model", "ifs_no", pre=True)
    def _normalize_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class SystemRoomBulkPayload(BaseModel):
    items: list[SystemRoomItemKey]


def _system_room_key_to_dict(key: SystemRoomItemKey) -> dict[str, Optional[str]]:
    return {
        "item_type": key.item_type,
        "donanim_tipi": key.donanim_tipi,
        "marka": key.marka,
        "model": key.model,
        "ifs_no": key.ifs_no,
    }


class InventoryAssignForm(BaseModel):
    envanter_no: str
    bilgisayar_adi: Optional[str] = None
    fabrika: Optional[str] = None
    departman: Optional[str] = None
    sorumlu_personel: Optional[str] = None
    kullanim_alani: Optional[str] = None
    seri_no: Optional[str] = None
    bagli_envanter_no: Optional[str] = None
    notlar: Optional[str] = None
    ifs_no: Optional[str] = None
    marka: Optional[str] = None
    model: Optional[str] = None
    donanim_tipi: Optional[str] = None


class LicenseAssignForm(BaseModel):
    lisans_adi: Optional[str] = None
    lisans_anahtari: Optional[str] = None
    sorumlu_personel: Optional[str] = None
    bagli_envanter_no: Optional[str] = None
    mail_adresi: Optional[str] = None
    ifs_no: Optional[str] = None


class PrinterAssignForm(BaseModel):
    envanter_no: str
    marka: Optional[str] = None
    model: Optional[str] = None
    kullanim_alani: Optional[str] = None
    ip_adresi: Optional[str] = None
    mac: Optional[str] = None
    hostname: Optional[str] = None
    ifs_no: Optional[str] = None
    bagli_envanter_no: Optional[str] = None
    sorumlu_personel: Optional[str] = None
    fabrika: Optional[str] = None
    notlar: Optional[str] = None


class AssignPayload(BaseModel):
    """Stok atama isteği."""

    stock_id: str = Field(..., description="donanim|marka|model|ifs biçiminde kimlik")
    atama_turu: Literal["lisans", "envanter", "yazici"]
    miktar: int = 1
    notlar: Optional[str] = None

    envanter_form: Optional[InventoryAssignForm] = None
    license_form: Optional[LicenseAssignForm] = None
    printer_form: Optional[PrinterAssignForm] = None


@router.get("/options", response_model=list[StockOption])
def stock_options(db: Session = Depends(get_db), q: Optional[str] = None):
    """Miktarı > 0 olan stokları döndür."""

    status = stock_status_detail(db)
    items: list[StockOption] = []
    q_lower = q.lower() if q else None

    for row in status["items"]:
        qty = row["net"]
        if qty <= 0:
            continue
        parts = [
            row["donanim_tipi"],
            row.get("marka"),
            row.get("model"),
            row.get("ifs_no"),
        ]
        label_parts = [p for p in parts if p]
        if q_lower and all(q_lower not in (p or "").lower() for p in label_parts):
            continue
        label = " | ".join(label_parts + [f"Mevcut:{qty}"])
        stock_id = "|".join(
            [
                row["donanim_tipi"],
                row.get("marka") or "",
                row.get("model") or "",
                row.get("ifs_no") or "",
            ]
        )
        items.append(
            StockOption(
                id=stock_id,
                label=label,
                donanim_tipi=row["donanim_tipi"],
                marka=row.get("marka"),
                model=row.get("model"),
                ifs_no=row.get("ifs_no"),
                lisans_anahtari=row.get("lisans_anahtari"),
                mail_adresi=row.get("mail_adresi"),
                mevcut_miktar=qty,
                source_type=row.get("source_type"),
                source_id=row.get("source_id"),
            )
        )

    return items


@api_router.post("/system-room/add")
def system_room_add(
    payload: SystemRoomBulkPayload,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Herhangi bir kayıt seçilmedi.")

    actor = (
        getattr(user, "full_name", None) or getattr(user, "username", "") or "Sistem"
    )
    added = 0
    skipped = 0

    for key in payload.items:
        data = _system_room_key_to_dict(key)
        exists = db.query(SystemRoomItem).filter_by(**data).first()
        if exists:
            skipped += 1
            continue
        entry = SystemRoomItem(**data, assigned_at=datetime.utcnow(), assigned_by=actor)
        db.add(entry)
        added += 1

    if added:
        db.commit()
    else:
        db.rollback()
    return {"ok": True, "added": added, "skipped": skipped}


@api_router.post("/system-room/remove")
def system_room_remove(
    payload: SystemRoomBulkPayload,
    db: Session = Depends(get_db),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Herhangi bir kayıt seçilmedi.")

    removed = 0
    for key in payload.items:
        data = _system_room_key_to_dict(key)
        query = db.query(SystemRoomItem)
        for field, value in data.items():
            column = getattr(SystemRoomItem, field)
            if value is None:
                query = query.filter(column.is_(None))
            else:
                query = query.filter(column == value)
        removed += query.delete(synchronize_session=False)

    db.commit()
    return {"ok": True, "removed": removed}


@api_router.get("/assign/source-detail")
def stock_assign_source_detail(
    source_type: Literal["envanter", "lisans", "yazici"] = Query(..., alias="type"),
    source_id: int = Query(..., alias="id"),
    db: Session = Depends(get_db),
):
    """Seçilen stok kaynağının temel bilgilerini döndür."""

    if source_type == "envanter":
        item = db.get(Inventory, source_id)
        if not item:
            raise HTTPException(status_code=404, detail="Envanter kaydı bulunamadı.")
        data = {
            "envanter_no": item.no,
            "bilgisayar_adi": item.bilgisayar_adi,
            "fabrika": item.fabrika,
            "departman": item.departman,
            "sorumlu_personel": item.sorumlu_personel,
            "kullanim_alani": item.kullanim_alani,
            "seri_no": item.seri_no,
            "bagli_envanter_no": item.bagli_envanter_no,
            "ifs_no": item.ifs_no,
            "donanim_tipi": item.donanim_tipi,
            "marka": item.marka,
            "model": item.model,
            "notlar": item.not_,
        }
    elif source_type == "lisans":
        item = db.get(License, source_id)
        if not item:
            raise HTTPException(status_code=404, detail="Lisans kaydı bulunamadı.")
        data = {
            "lisans_adi": item.lisans_adi,
            "lisans_anahtari": item.lisans_anahtari,
            "mail_adresi": item.mail_adresi,
            "sorumlu_personel": item.sorumlu_personel,
            "bagli_envanter_no": item.bagli_envanter_no
            or (item.inventory.no if item.inventory else None),
            "ifs_no": item.ifs_no,
            "donanim_tipi": item.lisans_adi,
        }
    else:  # yazici
        item = db.get(Printer, source_id)
        if not item:
            raise HTTPException(status_code=404, detail="Yazıcı kaydı bulunamadı.")
        data = {
            "envanter_no": item.envanter_no,
            "marka": item.marka,
            "model": item.model,
            "kullanim_alani": item.kullanim_alani,
            "ip_adresi": item.ip_adresi,
            "mac": item.mac,
            "hostname": item.hostname,
            "ifs_no": item.ifs_no,
            "bagli_envanter_no": item.bagli_envanter_no,
            "sorumlu_personel": item.sorumlu_personel,
            "fabrika": item.fabrika,
            "notlar": item.notlar,
        }

    return {"type": source_type, "data": data}


@router.post("/assign")
def stock_assign(
    payload: AssignPayload,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """Stoktaki bir kaydı ilgili modülde yeni kayıt oluşturarak atar."""

    try:
        parts = payload.stock_id.split("|", 3)
        donanim_tipi, marka_key, model_key, ifs_no = (
            parts[0],
            parts[1] if len(parts) > 1 else "",
            parts[2] if len(parts) > 2 else "",
            parts[3] if len(parts) > 3 else "",
        )
    except ValueError:  # pragma: no cover - validation
        raise HTTPException(status_code=400, detail="Geçersiz stok kimliği.")

    marka_key = marka_key or None
    model_key = model_key or None
    ifs_no = ifs_no or None

    def _build_lookup(model_cls):
        lookup: dict[str, str] = {}
        for row in db.query(model_cls).all():
            name = getattr(row, "name", None)
            if not name:
                continue
            lookup[str(row.id)] = str(name)
        return lookup

    def _build_reverse(mapping: dict[str, str]) -> dict[str, str]:
        return {
            str(value).strip().casefold(): key
            for key, value in mapping.items()
            if value
        }

    type_lookup = _build_lookup(HardwareType)
    # Lisans adları da stok loglarında saklanabildiği için aynı sözlüğe ekle.
    type_lookup.update(_build_lookup(LicenseName))
    type_reverse = _build_reverse(type_lookup)
    brand_lookup = _build_lookup(Brand)
    brand_reverse = _build_reverse(brand_lookup)
    model_lookup = _build_lookup(Model)
    model_reverse = _build_reverse(model_lookup)

    def _canon(
        value,
        lookup: Optional[dict[str, str]] = None,
        reverse: Optional[dict[str, str]] = None,
    ) -> str:
        if value is None:
            return ""
        value_str = str(value).strip()
        if not value_str:
            return ""
        if lookup:
            mapped = lookup.get(value_str)
            if mapped:
                return str(mapped).strip().casefold()
            if reverse:
                alt_key = reverse.get(value_str.casefold())
                if alt_key:
                    mapped_alt = lookup.get(alt_key)
                    if mapped_alt:
                        return str(mapped_alt).strip().casefold()
        return value_str.casefold()

    target_type = _canon(donanim_tipi, type_lookup, type_reverse)
    target_brand = _canon(marka_key, brand_lookup, brand_reverse)
    target_model = _canon(model_key, model_lookup, model_reverse)
    target_ifs = _canon(ifs_no)

    status = stock_status_detail(db)
    item = None
    for r in status["items"]:
        if (
            _canon(r["donanim_tipi"], type_lookup, type_reverse) == target_type
            and _canon(r.get("marka"), brand_lookup, brand_reverse) == target_brand
            and _canon(r.get("model"), model_lookup, model_reverse) == target_model
            and _canon(r.get("ifs_no")) == target_ifs
        ):
            item = r
            break

    if not item:
        raise HTTPException(status_code=404, detail="Stok kaydı bulunamadı.")

    donanim_tipi = item["donanim_tipi"]
    marka_key = item.get("marka")
    model_key = item.get("model")
    ifs_no = item.get("ifs_no") or ifs_no

    mevcut = item["net"]

    if payload.miktar <= 0:
        raise HTTPException(status_code=400, detail="Miktar 0'dan büyük olmalı.")
    if payload.miktar > mevcut:
        raise HTTPException(
            status_code=400,
            detail="Stoktaki mevcut miktardan fazla atayamazsınız.",
        )

    db.rollback()

    actor = (
        getattr(user, "full_name", None) or getattr(user, "username", None) or "system"
    )

    def _normalize_json(value):
        if isinstance(value, dict):
            return {k: _normalize_json(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_normalize_json(v) for v in value]
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    log_query = db.query(StockLog).filter(StockLog.donanim_tipi == donanim_tipi)
    if marka_key:
        log_query = log_query.filter(StockLog.marka == marka_key)
    else:
        log_query = log_query.filter(StockLog.marka.is_(None))
    if model_key:
        log_query = log_query.filter(StockLog.model == model_key)
    else:
        log_query = log_query.filter(StockLog.model.is_(None))
    if ifs_no:
        log_query = log_query.filter(StockLog.ifs_no == ifs_no)
    else:
        log_query = log_query.filter(StockLog.ifs_no.is_(None))
    last_log = log_query.order_by(StockLog.tarih.desc(), StockLog.id.desc()).first()

    created_id: Optional[int] = None
    assignment_target: Optional[str] = None
    assignment_person: Optional[str] = None
    assignment_usage: Optional[str] = None
    remaining = mevcut

    ctx = db.begin_nested if db.in_transaction() else db.begin

    with ctx():
        if payload.atama_turu == "envanter":
            if payload.miktar != 1:
                raise HTTPException(
                    status_code=400,
                    detail="Envanter atamalarında miktar 1 olmalıdır.",
                )
            form = payload.envanter_form
            if not form:
                raise HTTPException(status_code=422, detail="Envanter bilgileri eksik.")

            donanim_value = form.donanim_tipi or donanim_tipi
            marka_value = (
                form.marka
                or item.get("marka")
                or (last_log.marka if last_log else None)
            )
            model_value = (
                form.model
                or item.get("model")
                or (last_log.model if last_log else None)
            )

            if donanim_value and donanim_value.isdigit():
                hw = db.get(HardwareType, int(donanim_value))
                if hw:
                    donanim_value = hw.name
            if marka_value and marka_value.isdigit():
                brand_obj = db.get(Brand, int(marka_value))
                if brand_obj:
                    marka_value = brand_obj.name
            if model_value and model_value.isdigit():
                model_obj = db.get(Model, int(model_value))
                if model_obj:
                    model_value = model_obj.name

            inv = Inventory(
                no=form.envanter_no,
                bilgisayar_adi=form.bilgisayar_adi or None,
                fabrika=form.fabrika or None,
                departman=form.departman or None,
                donanim_tipi=donanim_value,
                marka=marka_value,
                model=model_value,
                seri_no=form.seri_no or None,
                sorumlu_personel=form.sorumlu_personel or None,
                bagli_envanter_no=form.bagli_envanter_no or None,
                kullanim_alani=form.kullanim_alani or None,
                ifs_no=form.ifs_no or ifs_no or (last_log.ifs_no if last_log else None),
                not_=form.notlar or None,
                tarih=datetime.utcnow(),
                islem_yapan=actor,
            )
            db.add(inv)
            db.flush()
            db.refresh(inv)
            db.add(
                InventoryLog(
                    inventory_id=inv.id,
                    action="create",
                    before_json=None,
                    after_json=(
                        _normalize_json(inv.to_dict())
                        if hasattr(inv, "to_dict")
                        else None
                    ),
                    note="Stok ataması ile oluşturuldu",
                    actor=actor,
                    created_at=datetime.utcnow(),
                )
            )
            created_id = inv.id
            assignment_target = inv.no
            assignment_person = form.sorumlu_personel or None
            assignment_usage = form.kullanim_alani or None
        elif payload.atama_turu == "lisans":
            if payload.miktar != 1:
                raise HTTPException(
                    status_code=400,
                    detail="Lisans atamalarında miktar 1 olmalıdır.",
                )
            form = payload.license_form
            if not form:
                raise HTTPException(status_code=422, detail="Lisans bilgileri eksik.")
            lisans_adi = form.lisans_adi or donanim_tipi
            if lisans_adi and lisans_adi.isdigit():
                lic_name = db.get(LicenseName, int(lisans_adi))
                if lic_name:
                    lisans_adi = lic_name.name

            env = None
            if form.bagli_envanter_no:
                env = (
                    db.query(Inventory)
                    .filter(Inventory.no == form.bagli_envanter_no)
                    .first()
                )

            lic = License(
                lisans_adi=lisans_adi,
                lisans_anahtari=form.lisans_anahtari
                or (last_log.lisans_anahtari if last_log else None),
                sorumlu_personel=form.sorumlu_personel or None,
                bagli_envanter_no=form.bagli_envanter_no or getattr(env, "no", None),
                inventory_id=env.id if env else None,
                ifs_no=form.ifs_no or ifs_no or (last_log.ifs_no if last_log else None),
                mail_adresi=form.mail_adresi
                or (last_log.mail_adresi if last_log else None),
                tarih=datetime.utcnow(),
                islem_yapan=actor,
            )
            db.add(lic)
            db.flush()
            db.refresh(lic)
            db.add(
                LicenseLog(
                    license_id=lic.id,
                    islem="EKLE",
                    detay="Stok ataması ile oluşturuldu",
                    islem_yapan=actor,
                )
            )
            created_id = lic.id
            assignment_target = lic.bagli_envanter_no
            assignment_person = form.sorumlu_personel or None
        elif payload.atama_turu == "yazici":
            if payload.miktar != 1:
                raise HTTPException(
                    status_code=400,
                    detail="Yazıcı atamalarında miktar 1 olmalıdır.",
                )
            form = payload.printer_form
            if not form:
                raise HTTPException(status_code=422, detail="Yazıcı bilgileri eksik.")

            marka_value = (
                form.marka
                or item.get("marka")
                or (last_log.marka if last_log else None)
            )
            model_value = (
                form.model
                or item.get("model")
                or (last_log.model if last_log else None)
            )
            if marka_value and marka_value.isdigit():
                brand_obj = db.get(Brand, int(marka_value))
                if brand_obj:
                    marka_value = brand_obj.name
            if model_value and model_value.isdigit():
                model_obj = db.get(Model, int(model_value))
                if model_obj:
                    model_value = model_obj.name

            printer = Printer(
                envanter_no=form.envanter_no,
                marka=marka_value,
                model=model_value,
                kullanim_alani=form.kullanim_alani or None,
                ip_adresi=form.ip_adresi or None,
                mac=form.mac or None,
                hostname=form.hostname or None,
                ifs_no=form.ifs_no or ifs_no or (last_log.ifs_no if last_log else None),
                bagli_envanter_no=form.bagli_envanter_no or None,
                sorumlu_personel=form.sorumlu_personel or None,
                fabrika=form.fabrika or None,
                notlar=form.notlar or None,
                tarih=datetime.utcnow(),
                islem_yapan=actor,
            )
            db.add(printer)
            db.flush()
            db.refresh(printer)
            db.add(
                PrinterHistory(
                    printer_id=printer.id,
                    action="create",
                    changes={},
                    actor=actor,
                    created_at=datetime.utcnow(),
                )
            )
            created_id = printer.id
            assignment_target = printer.envanter_no
            assignment_person = form.sorumlu_personel or None
            assignment_usage = form.kullanim_alani or None
        else:  # pragma: no cover - validation
            raise HTTPException(status_code=400, detail="Geçersiz atama türü.")

        total = db.execute(
            select(StockTotal)
            .where(StockTotal.donanim_tipi == donanim_tipi)
            .with_for_update()
        ).scalar_one_or_none()
        if not total or total.toplam < payload.miktar:
            raise HTTPException(status_code=400, detail="Yetersiz stok.")

        total.toplam -= payload.miktar
        remaining = total.toplam
        db.merge(total)

        db.add(
            StockAssignment(
                donanim_tipi=donanim_tipi,
                miktar=payload.miktar,
                ifs_no=ifs_no,
                hedef_envanter_no=assignment_target,
                sorumlu_personel=assignment_person,
                kullanim_alani=assignment_usage,
                actor=actor,
            )
        )

        create_stock_log(
            db,
            donanim_tipi=donanim_tipi,
            marka=item.get("marka") if item else None,
            model=item.get("model") if item else None,
            miktar=payload.miktar,
            ifs_no=ifs_no,
            islem="cikti",
            actor=actor,
            aciklama=payload.notlar,
            source_type=payload.atama_turu,
            source_id=created_id,
        )

    return {
        "ok": True,
        "message": "Atama tamamlandı.",
        "kalan_miktar": remaining,
    }
