from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from models import Printer, PrinterLog
from .printer_schemas import PrinterCreate, PrinterUpdate
from auth import get_db

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/printers", tags=["Yazıcılar"])


@router.get("", response_class=HTMLResponse)
def printer_list(request: Request, db: Session = Depends(get_db)):
    rows = (
        db.query(
            Printer.id,
            Printer.envanter_no,
            Printer.yazici_markasi,
            Printer.yazici_modeli,
            Printer.kullanim_alani,
            Printer.ip_adresi,
            Printer.mac,
            Printer.hostname,
        )
        .order_by(Printer.id.desc())
        .all()
    )
    return templates.TemplateResponse("printer_list.html", {"request": request, "rows": rows})


@router.get("/{printer_id}", response_class=HTMLResponse)
def printer_detail(printer_id: int, request: Request, db: Session = Depends(get_db)):
    prn = db.query(Printer).filter(Printer.id == printer_id).first()
    if not prn:
        raise HTTPException(404, "Yazıcı bulunamadı")

    logs = (
        db.query(PrinterLog)
        .filter(PrinterLog.printer_id == prn.id)
        .order_by(PrinterLog.changed_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "printer_detail.html", {"request": request, "item": prn, "logs": logs}
    )


@router.post("")
def create_printer(payload: PrinterCreate, db: Session = Depends(get_db)):
    prn = Printer(**payload.model_dump())
    db.add(prn)
    db.commit()
    return {"ok": True, "id": prn.id}


@router.post("/{printer_id}/update")
def update_printer(printer_id: int, payload: PrinterUpdate, db: Session = Depends(get_db)):
    prn = db.query(Printer).filter(Printer.id == printer_id).first()
    if not prn:
        raise HTTPException(404, "Yazıcı yok")

    mutable_fields = [
        "envanter_no",
        "yazici_markasi",
        "yazici_modeli",
        "kullanim_alani",
        "ip_adresi",
        "mac",
        "hostname",
        "ifs_no",
        "tarih",
        "islem_yapan",
        "sorumlu_personel",
    ]

    changer = payload.islem_yapan or "Sistem"
    changed = False

    for f in mutable_fields:
        new_val = getattr(payload, f, None)
        if new_val is None:
            continue
        old_val = getattr(prn, f)
        if new_val != old_val:
            setattr(prn, f, new_val)
            db.add(
                PrinterLog(
                    printer_id=prn.id,
                    field=f,
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val) if new_val is not None else None,
                    changed_by=changer,
                )
            )
            changed = True

    if changed:
        db.commit()
    return {"ok": True}
