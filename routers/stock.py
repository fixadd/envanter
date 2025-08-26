from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    PlainTextResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_db
from security import SessionUser, current_user
from models import StockAssignment, StockLog


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
        ws.append(
            [
                l.id,
                l.donanim_tipi,
                l.miktar,
                l.ifs_no,
                l.tarih,
                l.islem,
                l.actor,
            ]
        )

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
        .filter(StockLog.islem.in_(["cikti", "atama"]))
        .group_by(StockLog.donanim_tipi, StockLog.ifs_no)
        .subquery()
    )

    rows = (
        db.query(
            plus.c.donanim_tipi,
            plus.c.ifs_no,
            (func.coalesce(plus.c.sum_plus, 0) - func.coalesce(minus.c.sum_minus, 0)).label(
                "stok"
            ),
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
    return templates.TemplateResponse(
        "stock_list.html", {"request": request, "logs": logs}
    )


@router.post("/log")
def add_log(
    donanim_tipi: str = Form(...),
    miktar: int = Form(...),
    ifs_no: str | None = Form(None),
    islem: str = Form(...),
    db: Session = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    if islem not in ("girdi", "cikti"):
        raise HTTPException(status_code=400, detail="islem sadece girdi|cikti olabilir")
    if miktar <= 0:
        raise HTTPException(status_code=400, detail="miktar > 0 olmalı")

    actor = getattr(user, "full_name", None) if user else None
    log = StockLog(
        donanim_tipi=donanim_tipi,
        miktar=miktar,
        ifs_no=ifs_no,
        islem=islem,
        actor=actor,
        tarih=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    return RedirectResponse(url="/stock", status_code=303)


@router.get("/durum")
def stock_status(db: Session = Depends(get_db)):
    return JSONResponse({"ok": True, "rows": current_stock(db)})


@router.post("/assign")
def assign_stock(
    donanim_tipi: str = Form(...),
    miktar: int = Form(...),
    ifs_no: str | None = Form(None),
    hedef_envanter_no: str | None = Form(None),
    sorumlu_personel: str | None = Form(None),
    kullanim_alani: str | None = Form(None),
    db: Session = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    if miktar <= 0:
        raise HTTPException(status_code=400, detail="miktar > 0 olmalı")

    snapshot = current_stock(db)
    match = next(
        (r for r in snapshot if r["donanim_tipi"] == donanim_tipi and r["ifs_no"] == ifs_no),
        None,
    )
    mevcut = match["stok"] if match else 0
    if mevcut < miktar:
        raise HTTPException(status_code=400, detail=f"Yetersiz stok. Mevcut: {mevcut}")

    actor = getattr(user, "full_name", None) if user else None

    atama = StockAssignment(
        donanim_tipi=donanim_tipi,
        miktar=miktar,
        ifs_no=ifs_no,
        hedef_envanter_no=hedef_envanter_no,
        sorumlu_personel=sorumlu_personel,
        kullanim_alani=kullanim_alani,
        actor=actor,
        tarih=datetime.utcnow(),
    )
    db.add(atama)
    db.flush()

    db.add(
        StockLog(
            donanim_tipi=donanim_tipi,
            miktar=miktar,
            ifs_no=ifs_no,
            islem="atama",
            actor=actor,
            tarih=datetime.utcnow(),
        )
    )

    db.commit()
    return JSONResponse({"ok": True})

