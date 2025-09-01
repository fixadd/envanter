# routers/logs.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Inventory, InventoryLog, User

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
    users = [u[0] for u in db.query(User.username).order_by(User.username).all()]
    inventory_numbers = [i[0] for i in db.query(Inventory.no).order_by(Inventory.no).all()]
    return templates.TemplateResponse(
        "logs/index.html",
        {
            "request": request,
            "user_logs": user_logs,
            "inventory_logs": inventory_logs,
            "users": users,
            "inventory_numbers": inventory_numbers,
        },
    )
