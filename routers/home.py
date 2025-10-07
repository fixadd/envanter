# routers/home.py
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Inventory,
    InventoryLog,
    License,
    LicenseLog,
    Printer,
    StockLog,
    User,
)

FAULTY_STATUS = "ar\u0131zal\u0131"

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    """Render dashboard with live statistics."""

    active_inventory = or_(Inventory.durum.is_(None), Inventory.durum != "hurda")
    active_printers = or_(Printer.durum.is_(None), Printer.durum != "hurda")
    active_licenses = or_(
        License.durum.is_(None), ~License.durum.in_(["hurda", "stok"])
    )

    total_inventory = (
        db.query(func.count(Inventory.id)).filter(active_inventory).scalar() or 0
    )
    total_printers = (
        db.query(func.count(Printer.id)).filter(active_printers).scalar() or 0
    )

    lisans_sayisi = (
        db.query(func.count(License.id)).filter(active_licenses).scalar() or 0
    )
    bos_lisans_sayisi = (
        db.query(func.count(License.id))
        .filter(License.inventory_id.is_(None))
        .filter(active_licenses)
        .scalar()
        or 0
    )

    faulty_inventory = (
        db.query(func.count(Inventory.id))
        .filter(Inventory.durum == FAULTY_STATUS)
        .scalar()
        or 0
    )
    faulty_printers = (
        db.query(func.count(Printer.id))
        .filter(Printer.durum == FAULTY_STATUS)
        .scalar()
        or 0
    )

    try:
        bekleyen_talep = db.execute(
            text("SELECT COUNT(*) FROM requests WHERE durum='acik'")
        ).scalar()
    except Exception:
        bekleyen_talep = 0

    inv_logs = (
        db.query(
            InventoryLog.created_at,
            InventoryLog.actor,
            InventoryLog.action,
            Inventory.no.label("no"),
        )
        .join(Inventory, Inventory.id == InventoryLog.inventory_id)
        .all()
    )

    stock_logs = db.query(
        StockLog.tarih.label("created_at"),
        StockLog.actor,
        StockLog.islem.label("action"),
        StockLog.donanim_tipi.label("no"),
    ).all()

    license_logs = (
        db.query(
            LicenseLog.tarih.label("created_at"),
            LicenseLog.islem_yapan.label("actor"),
            LicenseLog.islem.label("action"),
            License.lisans_adi.label("no"),
        )
        .join(License, License.id == LicenseLog.license_id)
        .all()
    )

    actors = {
        log.actor
        for log in [*inv_logs, *stock_logs, *license_logs]
        if getattr(log, "actor", None)
    }
    user_map: dict[str, str] = {}
    if actors:
        users = (
            db.query(User.username, User.first_name, User.last_name, User.full_name)
            .filter(User.username.in_(actors))
            .all()
        )
        for u in users:
            full_name = u.full_name or f"{u.first_name} {u.last_name}".strip()
            user_map[u.username] = full_name or u.username

    son_islemler = [
        SimpleNamespace(
            created_at=log.created_at,
            actor=user_map.get(log.actor, log.actor),
            action=log.action,
            no=log.no,
        )
        for log in [*inv_logs, *stock_logs, *license_logs]
    ]

    son_islemler.sort(key=lambda x: x.created_at, reverse=True)
    son_islemler = son_islemler[:5]

    stats = {
        "toplam_cihaz": total_inventory + total_printers,
        "envanter_sayisi": total_inventory,
        "yazici_sayisi": total_printers,
        "lisans_sayisi": lisans_sayisi,
        "bos_lisans_sayisi": bos_lisans_sayisi,
        "arizali_cihaz_sayisi": faulty_inventory + faulty_printers,
        "bekleyen_talep": bekleyen_talep,
        "son_islemler": son_islemler,
    }

    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "stats": stats}
    )
