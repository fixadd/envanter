from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse, RedirectResponse
from datetime import datetime

from models import Printer, PrinterLog, Brand, Model
from auth import get_db

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/printers", tags=["Yazıcılar"])


@router.get("", response_class=HTMLResponse)
def printer_list(request: Request, db: Session = Depends(get_db)):
    rows = db.query(Printer).order_by(Printer.id.desc()).all()
    return templates.TemplateResponse(
        "printer_list.html", {"request": request, "rows": rows}
    )


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


@router.get("/create", response_class=HTMLResponse)
def printer_create_form(request: Request):
    return templates.TemplateResponse("printer_create.html", {"request": request})


@router.post("")
async def create_printer(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    prn = Printer(
        envanter_no=form.get("envanter_no"),
        brand_id=int(form.get("brand_id")) if form.get("brand_id") else None,
        model_id=int(form.get("model_id")) if form.get("model_id") else None,
        kullanim_alani=form.get("kullanim_alani"),
        ip_adresi=form.get("ip_adresi"),
        mac=form.get("mac"),
        hostname=form.get("hostname"),
        ifs_no=form.get("ifs_no"),
        tarih=form.get("tarih"),
        islem_yapan=form.get("islem_yapan"),
    )
    db.add(prn)
    db.commit()
    return RedirectResponse("/printers", status_code=303)


@router.get("/{printer_id}/edit", response_class=HTMLResponse)
def printer_edit(printer_id: int, request: Request, db: Session = Depends(get_db)):
    prn = db.query(Printer).filter(Printer.id == printer_id).first()
    if not prn:
        raise HTTPException(404, "Yazıcı bulunamadı")
    return templates.TemplateResponse(
        "printer_edit.html", {"request": request, "item": prn}
    )


def _pretty_change(field: str, old, new, db: Session):
    if field == "brand_id":
        get = lambda _id: db.query(Brand).get(_id).name if _id else None
        return ("brand", get(old), get(new))
    if field == "model_id":
        get = lambda _id: db.query(Model).get(_id).name if _id else None
        return ("model", get(old), get(new))
    return (field, old, new)


@router.post("/{printer_id}/update")
async def update_printer(printer_id: int, request: Request, db: Session = Depends(get_db)):
    prn = db.query(Printer).filter(Printer.id == printer_id).first()
    if not prn:
        raise HTTPException(404, "Yazıcı yok")

    form = await request.form()
    mutable_fields = [
        "envanter_no",
        "kullanim_alani",
        "ip_adresi",
        "mac",
        "hostname",
        "ifs_no",
        "tarih",
        "islem_yapan",
        "sorumlu_personel",
        "brand_id",
        "model_id",
    ]

    changer = form.get("islem_yapan") or "Sistem"
    changed = False

    for f in mutable_fields:
        raw_val = form.get(f)
        new_val = int(raw_val) if f.endswith("_id") and raw_val else raw_val
        old_val = getattr(prn, f)
        if new_val != old_val:
            setattr(prn, f, new_val)
            field_name, old_pretty, new_pretty = _pretty_change(f, old_val, new_val, db)
            db.add(
                PrinterLog(
                    printer_id=prn.id,
                    field=field_name,
                    old_value=str(old_pretty) if old_pretty is not None else None,
                    new_value=str(new_pretty) if new_pretty is not None else None,
                    changed_by=changer,
                )
            )
            changed = True

    if changed:
        db.commit()
    return RedirectResponse(f"/printers/{printer_id}", status_code=303)
