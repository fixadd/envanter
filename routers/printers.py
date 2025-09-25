from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Brand,
    Factory,
    Inventory,
    Model,
    Printer,
    PrinterHistory,
    ScrapPrinter,
    StockTotal,
    UsageArea,
)
from security import current_user
from utils.faults import FAULT_STATUS_SCRAP, resolve_fault
from utils.http import get_request_user_name
from utils.stock_log import create_stock_log

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/printers", tags=["Printers"])

USE_SCRAP_TABLE = True


@router.get("/export")
async def export_printers(db: Session = Depends(get_db)):
    """Export printer records as an Excel file."""
    from io import BytesIO

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    headers = [
        "ID",
        "Envanter No",
        "Marka",
        "Model",
        "Seri No",
        "Fabrika",
        "Kullanım Alanı",
        "Sorumlu Personel",
        "Bağlı Envanter No",
        "IP Adresi",
        "MAC",
        "Hostname",
        "IFS No",
        "Tarih",
        "İşlem Yapan",
        "Durum",
        "Notlar",
    ]
    ws.append(headers)

    rows = db.query(Printer).order_by(Printer.id.asc()).all()
    for r in rows:
        ws.append(
            [
                r.id,
                r.envanter_no,
                r.marka,
                r.model,
                r.seri_no,
                r.fabrika,
                r.kullanim_alani,
                r.sorumlu_personel,
                r.bagli_envanter_no,
                r.ip_adresi,
                r.mac,
                r.hostname,
                r.ifs_no,
                r.tarih,
                r.islem_yapan,
                r.durum,
                r.notlar,
            ]
        )

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    headers = {"Content-Disposition": "attachment; filename=printers.xlsx"}
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/import", response_class=PlainTextResponse)
async def import_printers(file: UploadFile = File(...)):
    return f"Received {file.filename}, but import is not implemented."


def build_changes(old: Printer, new_vals: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in new_vals.items():
        old_v = getattr(old, k, None)
        if (old_v or "") != (v or ""):
            out[k] = {"old": old_v, "new": v}
    return out


def snapshot(p: Printer) -> Dict[str, Any]:
    return {
        "id": p.id,
        "inventory_id": p.inventory_id,
        "marka": p.marka,
        "model": p.model,
        "seri_no": p.seri_no,
        "fabrika": p.fabrika,
        "kullanim_alani": p.kullanim_alani,
        "sorumlu_personel": p.sorumlu_personel,
        "bagli_envanter_no": p.bagli_envanter_no,
        "durum": p.durum,
        "notlar": p.notlar,
    }


def _printer_lookups(db: Session) -> dict[str, list[str]]:
    fabrika = [
        row.name
        for row in db.query(Factory).order_by(Factory.name.asc()).all()
        if (row.name or "").strip()
    ]
    departman = [
        row.name
        for row in db.query(UsageArea).order_by(UsageArea.name.asc()).all()
        if (row.name or "").strip()
    ]
    if not departman:
        departman = [
            val[0]
            for val in (
                db.query(Printer.kullanim_alani)
                .filter(Printer.kullanim_alani.isnot(None))
                .distinct()
                .order_by(Printer.kullanim_alani.asc())
                .all()
            )
            if (val[0] or "").strip()
        ]
    yazici_marka = [
        row.name for row in db.query(Brand).order_by(Brand.name.asc()).all()
    ]
    envanterler = [
        {
            "envanter_no": inv.no,
            "bilgisayar_adi": inv.bilgisayar_adi or "",
        }
        for inv in (
            db.query(Inventory)
            .filter(Inventory.durum != "hurda")
            .order_by(Inventory.no.asc())
            .all()
        )
    ]
    return {
        "fabrika": fabrika,
        "departman": departman,
        "yazici_marka": yazici_marka,
        "envanterler": envanterler,
    }


@router.get("", response_class=HTMLResponse)
def list_printers(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    durum: Optional[str] = None,
):
    query = db.query(Printer)
    if durum:
        query = query.filter(Printer.durum == durum)
    else:
        query = query.filter(Printer.durum != "hurda")
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Printer.marka.ilike(like))
            | (Printer.model.ilike(like))
            | (Printer.seri_no.ilike(like))
            | (Printer.sorumlu_personel.ilike(like))
            | (Printer.bagli_envanter_no.ilike(like))
            | (Printer.envanter_no.ilike(like))
            | (Printer.ip_adresi.ilike(like))
            | (Printer.hostname.ilike(like))
        )

    printers = query.order_by(Printer.id.desc()).all()
    lookups = _printer_lookups(db)
    current_id = request.query_params.get("id") or request.query_params.get("item")
    try:
        current_id_int = int(current_id) if current_id else None
    except (TypeError, ValueError):
        current_id_int = None
    current_item = db.get(Printer, current_id_int) if current_id_int else None
    context = {
        "request": request,
        "printers": printers,
        "lookups": lookups,
        "current_id": current_id_int,
        "current_item": current_item,
    }
    return templates.TemplateResponse("printers/index.html", context)


@router.get("/new", response_class=HTMLResponse)
def new_printer_form(request: Request):
    return templates.TemplateResponse("printer_create.html", {"request": request})


@router.post("", response_class=HTMLResponse)
def create_printer(
    request: Request,
    envanter_no: str = Form(...),
    marka_id: int = Form(None),
    model_id: int = Form(None),
    kullanim_alani_id: int = Form(None),
    ip_adresi: str = Form(""),
    mac: str = Form(""),
    hostname: str = Form(""),
    ifs_no: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    marka = db.get(Brand, marka_id) if marka_id else None
    model = db.get(Model, model_id) if model_id else None
    area = db.get(UsageArea, kullanim_alani_id) if kullanim_alani_id else None
    p = Printer(
        marka=marka.name if marka else None,
        model=model.name if model else None,
        envanter_no=envanter_no,
        ip_adresi=ip_adresi or None,
        mac=mac or None,
        hostname=hostname or None,
        ifs_no=ifs_no or None,
        kullanim_alani=area.name if area else None,
        tarih=datetime.utcnow(),
        islem_yapan=getattr(user, "full_name", None) or "system",
    )
    db.add(p)
    db.add(
        PrinterHistory(
            printer=p,
            action="create",
            changes={},
            actor=getattr(user, "full_name", None) or "system",
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    return RedirectResponse(url="/printers", status_code=303)


@router.post("/create")
def create_printer_simple(
    request: Request,
    envanter_no: str = Form(...),
    marka: str = Form(""),
    model: str = Form(""),
    departman: str = Form(""),
    fabrika: str = Form(""),
    ip: str = Form(""),
    mac: str = Form(""),
    bagli_envanter_no: str = Form(None),
    not_field: str = Form(None, alias="not"),
    yazici_markasi: str = Form(None),  # legacy fields
    yazici_modeli: str = Form(None),
    kullanim_alani: str = Form(None),
    ip_adresi: str = Form(None),
    hostname: str = Form(None),
    ifs_no: str = Form(None),
    db: Session = Depends(get_db),
):
    marka_value = marka or yazici_markasi or None
    model_value = model or yazici_modeli or None
    departman_value = departman or kullanim_alani or None
    ip_value = ip or ip_adresi or None
    note_value = not_field or None
    prn = Printer(
        envanter_no=envanter_no,
        marka=marka_value,
        model=model_value,
        fabrika=fabrika or None,
        kullanim_alani=departman_value,
        ip_adresi=ip_value,
        mac=mac or None,
        hostname=hostname or None,
        ifs_no=ifs_no or None,
        bagli_envanter_no=bagli_envanter_no or None,
        notlar=note_value,
        tarih=datetime.utcnow(),
        islem_yapan=get_request_user_name(request),
    )
    db.add(prn)
    db.commit()
    return RedirectResponse(url="/printers", status_code=303)


@router.get("/{printer_id}", response_class=HTMLResponse)
def printer_detail(printer_id: int, request: Request, db: Session = Depends(get_db)):
    p = db.get(Printer, printer_id)
    if not p or p.durum == "hurda":
        raise HTTPException(404, "Yazıcı bulunamadı")
    logs = (
        db.query(PrinterHistory)
        .filter(PrinterHistory.printer_id == p.id)
        .order_by(PrinterHistory.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "printers_detail.html", {"request": request, "p": p, "logs": logs}
    )


@router.post("/assign/{printer_id}")
def assign_printer(
    printer_id: int,
    fabrika: str = Form(None),
    kullanim_alani: str = Form(None),
    sorumlu_personel: str = Form(None),
    bagli_envanter_no: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    p = db.get(Printer, printer_id)
    if not p:
        raise HTTPException(404, "Yazıcı bulunamadı")

    new_vals = {
        "fabrika": fabrika,
        "kullanim_alani": kullanim_alani,
        "sorumlu_personel": sorumlu_personel,
        "bagli_envanter_no": bagli_envanter_no,
    }
    changes = build_changes(p, new_vals)
    for k, v in new_vals.items():
        setattr(p, k, v)

    db.add(
        PrinterHistory(
            printer_id=p.id,
            action="assign",
            changes=changes,
            actor=getattr(user, "full_name", None) or "system",
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    return JSONResponse({"ok": True})


@router.get("/{printer_id}/edit", response_class=HTMLResponse)
def edit_printer(
    printer_id: int,
    request: Request,
    modal: bool = False,
    db: Session = Depends(get_db),
):
    p = db.get(Printer, printer_id)
    if not p:
        raise HTTPException(404, "Yazıcı bulunamadı")
    return templates.TemplateResponse(
        "printers_edit.html", {"request": request, "p": p, "modal": modal}
    )


@router.post("/{printer_id}/edit")
def edit_printer_post(
    printer_id: int,
    marka: str = Form(None),
    model: str = Form(None),
    departman: str = Form(None),
    fabrika: str = Form(None),
    ip: str = Form(None),
    mac: str = Form(None),
    bagli_envanter_no: str = Form(None),
    not_field: str = Form(None, alias="not"),
    seri_no: str = Form(None),
    notlar: str = Form(None),
    modal: bool = False,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    p = db.get(Printer, printer_id)
    if not p:
        raise HTTPException(404, "Yazıcı bulunamadı")

    new_vals = {
        "marka": marka,
        "model": model,
        "seri_no": seri_no,
        "fabrika": fabrika,
        "kullanim_alani": departman,
        "ip_adresi": ip,
        "mac": mac,
        "bagli_envanter_no": bagli_envanter_no,
        "notlar": not_field if not_field is not None else notlar,
    }
    changes = build_changes(p, new_vals)
    for attr, value in new_vals.items():
        if value is not None:
            setattr(p, attr, value)

    db.add(
        PrinterHistory(
            printer_id=p.id,
            action="edit",
            changes=changes,
            actor=getattr(user, "full_name", None) or "system",
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    if modal:
        return HTMLResponse(
            "<script>window.parent.postMessage('modal-close','*');</script>"
        )
    return RedirectResponse(url=f"/printers/{printer_id}", status_code=303)


@router.get("/{printer_id}/stock")
def stock_printer(
    printer_id: int, db: Session = Depends(get_db), user=Depends(current_user)
):
    p = db.get(Printer, printer_id)
    if not p:
        raise HTTPException(404, "Yazıcı bulunamadı")
    actor = getattr(user, "full_name", None) or user.username
    donanim_tipi = "Yazıcı"

    # Yazıcı stok girişinde sorumluluk bilgilerini sıfırla
    p.sorumlu_personel = None
    p.bagli_envanter_no = None
    p.fabrika = "Baylan 3"

    create_stock_log(
        db,
        donanim_tipi=donanim_tipi,
        miktar=1,
        ifs_no=p.ifs_no,
        marka=p.marka,
        model=p.model,
        islem="girdi",
        actor=actor,
        source_type="yazici",
        source_id=p.id,
    )

    total = db.get(StockTotal, donanim_tipi) or StockTotal(
        donanim_tipi=donanim_tipi, toplam=0
    )
    total.toplam += 1
    db.merge(total)
    db.add(
        PrinterHistory(
            printer_id=p.id,
            action="stock",
            changes=None,
            actor=actor,
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    return RedirectResponse(url="/stock?tab=status&module=printer", status_code=303)


@router.post("/{printer_id}/scrap")
def scrap_printer(
    printer_id: int,
    reason: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    p = db.get(Printer, printer_id)
    if not p:
        raise HTTPException(404, "Yazıcı bulunamadı")

    before_status = p.durum
    p.durum = "hurda"

    db.add(
        PrinterHistory(
            printer_id=p.id,
            action="scrap",
            changes={
                "durum": {"old": before_status, "new": "hurda"},
                "reason": {"old": None, "new": reason},
            },
            actor=getattr(user, "full_name", None) or "system",
            created_at=datetime.utcnow(),
        )
    )

    if USE_SCRAP_TABLE:
        snap = snapshot(p)
        existing = db.query(ScrapPrinter).filter_by(printer_id=p.id).first()
        if existing:
            existing.snapshot = snap
            existing.reason = reason
            existing.created_at = datetime.utcnow()
        else:
            db.add(ScrapPrinter(printer_id=p.id, snapshot=snap, reason=reason))

    resolve_fault(
        db,
        "printer",
        entity_id=p.id,
        status=FAULT_STATUS_SCRAP,
        actor=getattr(user, "full_name", None) or getattr(user, "username", ""),
        note=reason or "Hurdaya ayrıldı",
    )

    db.commit()
    return JSONResponse({"ok": True})
