from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Printer, ScrapPrinter

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/printers", tags=["Printers - Scrap"])

USE_SCRAP_TABLE = True


@router.get("/scrap", name="Hurdalar")
def scrap_list(request: Request, db: Session = Depends(get_db)):
    if USE_SCRAP_TABLE:
        rows = db.query(ScrapPrinter).order_by(ScrapPrinter.created_at.desc()).all()
        return templates.TemplateResponse(
            "printers_scrap.html", {"request": request, "rows": rows, "mode": "table"}
        )
    else:
        rows = (
            db.query(Printer)
            .filter(Printer.durum == "hurda")
            .order_by(Printer.id.desc())
            .all()
        )
        return templates.TemplateResponse(
            "printers_scrap.html", {"request": request, "rows": rows, "mode": "filter"}
        )
