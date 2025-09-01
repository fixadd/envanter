# routers/logs.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Inventory, InventoryLog

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def logs_home(request: Request, db: Session = Depends(get_db)):
    user_logs = (
        db.query(InventoryLog, Inventory.no.label("inv_no"))
        .join(Inventory, Inventory.id == InventoryLog.inventory_id)
        .order_by(InventoryLog.created_at.desc())
        .all()
    )
    inventory_logs = (
        db.query(InventoryLog, Inventory.no.label("inv_no"))
        .join(Inventory, Inventory.id == InventoryLog.inventory_id)
        .order_by(InventoryLog.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "logs/index.html",
        {
            "request": request,
            "user_logs": user_logs,
            "inventory_logs": inventory_logs,
        },
    )
