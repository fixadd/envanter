# routers/home.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Inventory,
    InventoryLog,
    License,
    LicenseLog,
    Printer,
    StockLog,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    """Render dashboard with live statistics."""

    total_inventory = (
        db.query(func.count(Inventory.id)).filter(Inventory.durum != "hurda").scalar()
    )
    total_printers = (
        db.query(func.count(Printer.id)).filter(Printer.durum != "hurda").scalar()
    )
    toplam_cihaz = (total_inventory or 0) + (total_printers or 0)

    lisans_sayisi = (
        db.query(func.count(License.id)).filter(License.durum != "hurda").scalar() or 0
    )
    bos_lisans_sayisi = (
        db.query(func.count(License.id))
        .filter(License.inventory_id.is_(None), License.durum != "hurda")
        .scalar()
        or 0
    )

    arizali_cihaz_sayisi = (
        db.query(func.count(Inventory.id)).filter(Inventory.durum == "arızalı").scalar()
        or 0
    )
    arizali_cihaz_sayisi += (
        db.query(func.count(Printer.id)).filter(Printer.durum == "arızalı").scalar() or 0
    )

    try:
        bekleyen_talep = db.execute(
            text("SELECT COUNT(*) FROM requests WHERE durum='aktif'")
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

    son_islemler = sorted(
        [*inv_logs, *stock_logs, *license_logs],
        key=lambda x: x.created_at,
        reverse=True,
    )[:5]

    stats = {
        "toplam_cihaz": toplam_cihaz,
        "envanter_sayisi": total_inventory or 0,
        "yazici_sayisi": total_printers or 0,
        "lisans_sayisi": lisans_sayisi,
        "bos_lisans_sayisi": bos_lisans_sayisi,
        "arizali_cihaz_sayisi": arizali_cihaz_sayisi,
        "bekleyen_talep": bekleyen_talep,
        "son_islemler": son_islemler,
    }

    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "stats": stats}
    )
