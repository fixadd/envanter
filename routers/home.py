# routers/home.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import get_db
from models import Inventory, InventoryLog, License, Printer

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
        db.query(func.count(Printer.id)).filter(Printer.durum == "arızalı").scalar()
        or 0
    )

    try:
        bekleyen_talep = db.execute(
            text("SELECT COUNT(*) FROM requests WHERE durum='aktif'")
        ).scalar()
    except Exception:
        bekleyen_talep = 0

    son_islemler = (
        db.query(
            InventoryLog.created_at,
            InventoryLog.actor,
            InventoryLog.action,
            Inventory.no.label("no"),
        )
        .join(Inventory, Inventory.id == InventoryLog.inventory_id)
        .order_by(InventoryLog.created_at.desc())
        .limit(5)
        .all()
    )

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
