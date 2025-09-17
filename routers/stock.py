from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Body
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, text, select
from sqlalchemy.orm import Session
from typing import Optional, Literal
from pydantic import BaseModel, Field

from database import get_db
from models import (
    StockLog,
    HardwareType,
    UsageArea,
    LicenseName,
    StockTotal,
    Inventory,
    InventoryLog,
    License,
    LicenseLog,
    Printer,
    PrinterHistory,
    StockAssignment,
    Brand,
    Model,
)
from routers.api import stock_status_detail
from security import current_user

router = APIRouter(prefix="/stock", tags=["Stock"])
api_router = APIRouter(prefix="/api/stock", tags=["stock"])
templates = Jinja2Templates(directory="templates")

@router.get("/export")
async def export_stock(db: Session = Depends(get_db)):
    """Export stock logs as an Excel file."""
    from openpyxl import Workbook
    from io import BytesIO

    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Donanım Tipi", "Miktar", "IFS No", "Tarih", "İşlem", "İşlem Yapan"])

    logs = db.query(StockLog).order_by(StockLog.id.asc()).all()
    for log_entry in logs:
        ws.append([
            log_entry.id,
            log_entry.donanim_tipi,
            log_entry.miktar,
            log_entry.ifs_no,
            log_entry.tarih,
            log_entry.islem,
            log_entry.actor,
        ])

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    headers = {"Content-Disposition": "attachment; filename=stock_logs.xlsx"}
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )

@router.post("/import", response_class=PlainTextResponse)
async def import_stock(file: UploadFile = File(...)):
    return f"Received {file.filename}, but import is not implemented."

def current_stock(db: Session):
    plus = (
        db.query(
            StockLog.donanim_tipi,
            StockLog.ifs_no,
            func.sum(StockLog.miktar).label("sum_plus"),
        )
        .filter(StockLog.islem == "girdi")
        .group_by(StockLog.donanim_tipi, StockLog.ifs_no)
        .subquery()
    )

    minus = (
        db.query(
            StockLog.donanim_tipi,
            StockLog.ifs_no,
            func.sum(StockLog.miktar).label("sum_minus"),
        )
        .filter(StockLog.islem.in_(["cikti", "atama", "hurda"]))
        .group_by(StockLog.donanim_tipi, StockLog.ifs_no)
        .subquery()
    )

    rows = (
        db.query(
            plus.c.donanim_tipi,
            plus.c.ifs_no,
            (func.coalesce(plus.c.sum_plus, 0) - func.coalesce(minus.c.sum_minus, 0)).label("stok"),
        )
        .outerjoin(
            minus,
            (minus.c.donanim_tipi == plus.c.donanim_tipi)
            & (minus.c.ifs_no == plus.c.ifs_no),
        )
        .all()
    )

    orphan_minus = (
        db.query(
            minus.c.donanim_tipi,
            minus.c.ifs_no,
            (0 - func.coalesce(minus.c.sum_minus, 0)).label("stok"),
        )
        .outerjoin(
            plus,
            (plus.c.donanim_tipi == minus.c.donanim_tipi)
            & (plus.c.ifs_no == minus.c.ifs_no),
        )
        .filter(plus.c.donanim_tipi.is_(None))
        .all()
    )

    all_rows = rows + orphan_minus
    return [
        {"donanim_tipi": r[0], "ifs_no": r[1], "stok": int(r[2])} for r in all_rows
    ]

@router.get("", response_class=HTMLResponse)
def stock_list(request: Request, db: Session = Depends(get_db)):
    logs = db.query(StockLog).order_by(StockLog.tarih.desc(), StockLog.id.desc()).all()
    hardware_types = db.query(HardwareType).order_by(HardwareType.name).all()
    license_names = db.query(LicenseName).order_by(LicenseName.name).all()
    hardware_map = {str(h.id): h.name for h in hardware_types}
    license_map = {
        str(license_name.id): license_name.name for license_name in license_names
    }
    users = [r[0] for r in db.execute(text("SELECT full_name FROM users ORDER BY full_name")).fetchall()]
    usage_areas = db.query(UsageArea).order_by(UsageArea.name).all()
    return templates.TemplateResponse(
        "stock_list.html",
        {
            "request": request,
            "logs": logs,
            "hardware_types": hardware_types,
            "hardware_map": hardware_map,
            "license_map": license_map,
            "users": users,
            "usage_areas": usage_areas,
        },
    )

@router.get("/durum", response_class=HTMLResponse)
def stock_status_page(request: Request):
    """Stok durumunu HTML olarak göster."""
    return templates.TemplateResponse("stock.html", {"request": request})


@router.get("/durum/json")
def stock_status_json(db: Session = Depends(get_db)):
    """Stok durumunu JSON olarak döndür."""
    data = stock_status_detail(db)
    return JSONResponse({"ok": True, "totals": data["totals"], "items": data["items"]})


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
            }
        )
    return items

@router.post("/add")
def stock_add(payload: dict = Body(...), db: Session = Depends(get_db)):
    # UI yeni adla `is_lisans` gönderiyor; eski `is_license` ile de uyumlu
    # kalmak için her ikisini de kontrol ediyoruz.
    is_license = payload.get("is_lisans") or payload.get("is_license")
    donanim_tipi = payload.get("donanim_tipi")
    if donanim_tipi and donanim_tipi.isdigit():
        ht = db.get(HardwareType, int(donanim_tipi))
        if ht:
            donanim_tipi = ht.name
        else:
            ln = db.get(LicenseName, int(donanim_tipi))
            if ln:
                donanim_tipi = ln.name

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
    islem = payload.get("islem") or "girdi"

    total = db.get(StockTotal, donanim_tipi) or StockTotal(
        donanim_tipi=donanim_tipi, toplam=0
    )
    if islem in ("cikti", "hurda") and total.toplam < miktar:
        return {"ok": False, "error": "Yetersiz stok"}

    log = StockLog(
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
    db.add(log)

    total.toplam = total.toplam + miktar if islem == "girdi" else total.toplam - miktar
    db.merge(total)
    db.commit()
    return {"ok": True, "id": log.id}

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
        parts = [row["donanim_tipi"], row.get("marka"), row.get("model"), row.get("ifs_no")]
        label_parts = [p for p in parts if p]
        if q_lower and all(q_lower not in (p or "").lower() for p in label_parts):
            continue
        label = " | ".join(label_parts + [f"Mevcut:{qty}"])
        stock_id = "|".join([row["donanim_tipi"], row.get("marka") or "", row.get("model") or "", row.get("ifs_no") or ""])
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
            )
        )

    return items

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

    status = stock_status_detail(db)
    item = None
    for r in status["items"]:
        if (
            r["donanim_tipi"] == donanim_tipi
            and (marka_key or "") == (r.get("marka") or "")
            and (model_key or "") == (r.get("model") or "")
            and (ifs_no or "") == (r.get("ifs_no") or "")
        ):
            item = r
            break

    if not item:
        raise HTTPException(status_code=404, detail="Stok kaydı bulunamadı.")

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
        getattr(user, "full_name", None)
        or getattr(user, "username", None)
        or "system"
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
    last_log = (
        log_query.order_by(StockLog.tarih.desc(), StockLog.id.desc()).first()
    )

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
                raise HTTPException(
                    status_code=422, detail="Envanter bilgileri eksik."
                )

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
                    after_json=_normalize_json(inv.to_dict()) if hasattr(inv, "to_dict") else None,
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
                raise HTTPException(
                    status_code=422, detail="Lisans bilgileri eksik."
                )
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
                lisans_anahtari=
                    form.lisans_anahtari
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
                raise HTTPException(
                    status_code=422, detail="Yazıcı bilgileri eksik."
                )

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

        total = (
            db.execute(
                select(StockTotal)
                .where(StockTotal.donanim_tipi == donanim_tipi)
                .with_for_update()
            ).scalar_one_or_none()
        )
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

        db.add(
            StockLog(
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
        )

    return {
        "ok": True,
        "message": "Atama tamamlandı.",
        "kalan_miktar": remaining,
    }
