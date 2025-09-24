# routers/logs.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Inventory, InventoryLog, User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse, name="logs_page")
def logs_home(request: Request, tab: str = "kullanici", db: Session = Depends(get_db)):
    logs = (
        db.query(InventoryLog, Inventory.no.label("inv_no"))
        .join(Inventory, Inventory.id == InventoryLog.inventory_id)
        .order_by(InventoryLog.created_at.desc())
        .all()
    )
    users = [u[0] for u in db.query(User.username).order_by(User.username).all()]
    inventory_numbers = [
        i[0] for i in db.query(Inventory.no).order_by(Inventory.no).all()
    ]
    return templates.TemplateResponse(
        "logs/index.html",
        {
            "request": request,
            "user_logs": logs,
            "inventory_logs": logs,
            "users": users,
            "inventory_numbers": inventory_numbers,
            "tab": tab,
        },
    )
