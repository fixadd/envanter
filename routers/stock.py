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
    License,
    Printer,
)
from routers.api import stock_status

router = APIRouter(prefix="/stock", tags=["Stock"])
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
    for l in logs:
        ws.append([
            l.id,
            l.donanim_tipi,
            l.miktar,
            l.ifs_no,
            l.tarih,
            l.islem,
            l.actor,
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
    license_map = {str(l.id): l.name for l in license_names}
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
def stock_status_page(request: Request, db: Session = Depends(get_db)):
    rows = current_stock(db)
    return templates.TemplateResponse(
        "stock_status.html", {"request": request, "rows": rows}
    )

@router.get("/durum/json")
def stock_status_json(db: Session = Depends(get_db)):
    return JSONResponse({"ok": True, "rows": current_stock(db)})

@router.post("/add")
def stock_add(payload: dict = Body(...), db: Session = Depends(get_db)):
    is_license = payload.get("is_license")
    donanim_tipi = payload.get("donanim_tipi")
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
        marka=None if is_license else payload.get("marka"),
        model=None if is_license else payload.get("model"),
        lisans_anahtari=payload.get("lisans_anahtari") if is_license else None,
        mail_adresi=payload.get("mail_adresi") if is_license else None,
        miktar=miktar,
        ifs_no=payload.get("ifs_no") or None,
        aciklama=payload.get("aciklama"),
        islem=islem,
        tarih=datetime.utcnow(),
        actor=payload.get("islem_yapan") or "Sistem",
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
    ifs_no: Optional[str] = None
    mevcut_miktar: int

class AssignPayload(BaseModel):
    """Stok atama isteği."""

    stock_id: str = Field(..., description="donanim_tipi|ifs_no biçiminde kimlik")
    atama_turu: Literal["lisans", "envanter", "yazici"]
    miktar: int = 1

    hedef_envanter_id: Optional[int] = None
    hedef_yazici_id: Optional[int] = None
    lisans_id: Optional[int] = None
    sorumlu_personel_id: Optional[str] = None
    notlar: Optional[str] = None

@router.get("/options", response_model=list[StockOption])
def stock_options(db: Session = Depends(get_db), q: Optional[str] = None):
    """Miktarı > 0 olan stokları döndür."""

    status = stock_status(db)
    items: list[StockOption] = []
    q_lower = q.lower() if q else None

    for dt, total in status["totals"].items():
        detail = status["detail"].get(dt, {})
        if detail:
            for ifs, qty in detail.items():
                if qty <= 0:
                    continue
                if q_lower and q_lower not in dt.lower() and q_lower not in (ifs or "").lower():
                    continue
                items.append(
                    StockOption(
                        id=f"{dt}|{ifs}",
                        label=f"{dt or 'Donanım'} | IFS:{ifs or '-'} | Mevcut:{qty}",
                        donanim_tipi=dt,
                        ifs_no=ifs,
                        mevcut_miktar=qty,
                    )
                )
        elif total > 0:
            if q_lower and q_lower not in dt.lower():
                continue
            items.append(
                StockOption(
                    id=f"{dt}|",
                    label=f"{dt or 'Donanım'} | IFS:- | Mevcut:{total}",
                    donanim_tipi=dt,
                    mevcut_miktar=total,
                )
            )

    return items

@router.post("/assign")
def stock_assign(payload: AssignPayload, db: Session = Depends(get_db)):
    """Stoktaki bir kaydı lisans/envanter/yazıcıya atar."""

    try:
        donanim_tipi, ifs_no = payload.stock_id.split("|", 1)
    except ValueError:  # pragma: no cover - validation
        raise HTTPException(status_code=400, detail="Geçersiz stok kimliği.")
    ifs_no = ifs_no or None

    status = stock_status(db)
    mevcut = status["detail"].get(donanim_tipi, {}).get(ifs_no)
    if mevcut is None:
        mevcut = status["totals"].get(donanim_tipi, 0)

    if payload.miktar <= 0:
        raise HTTPException(status_code=400, detail="Miktar 0'dan büyük olmalı.")
    if payload.miktar > mevcut:
        raise HTTPException(
            status_code=400,
            detail="Stoktaki mevcut miktardan fazla atayamazsınız.",
        )

    personel = payload.sorumlu_personel_id

    # stock_status sorgusu otomatik olarak bir transaction başlatabilir.
    # Yeni işlem başlatmadan önce mevcut durumu sonlandır.
    db.rollback()

    with db.begin():
        if payload.atama_turu == "envanter":
            if not payload.hedef_envanter_id:
                raise HTTPException(status_code=422, detail="Hedef envanter seçiniz.")
            hedef = db.get(Inventory, payload.hedef_envanter_id)
            if not hedef:
                raise HTTPException(status_code=404, detail="Hedef envanter bulunamadı.")
            if ifs_no:
                hedef.ifs_no = ifs_no
            if personel:
                hedef.sorumlu_personel = personel
        elif payload.atama_turu == "yazici":
            if not payload.hedef_yazici_id:
                raise HTTPException(status_code=422, detail="Hedef yazıcı seçiniz.")
            hedef = db.get(Printer, payload.hedef_yazici_id)
            if not hedef:
                raise HTTPException(status_code=404, detail="Hedef yazıcı bulunamadı.")
            if personel:
                hedef.sorumlu_personel = personel
        elif payload.atama_turu == "lisans":
            if not payload.lisans_id:
                raise HTTPException(status_code=422, detail="Lisans seçiniz.")
            hedef = db.get(License, payload.lisans_id)
            if not hedef:
                raise HTTPException(status_code=404, detail="Lisans bulunamadı.")
            if personel:
                hedef.sorumlu_personel = personel
            if payload.hedef_envanter_id:
                env = db.get(Inventory, payload.hedef_envanter_id)
                if env:
                    hedef.bagli_envanter_no = env.no
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
        db.merge(total)

        db.add(
            StockLog(
                donanim_tipi=donanim_tipi,
                miktar=payload.miktar,
                ifs_no=ifs_no,
                islem="cikti",
                actor=personel,
            )
        )

    return {
        "ok": True,
        "message": "Atama tamamlandı.",
        "kalan_miktar": total.toplam,
    }
