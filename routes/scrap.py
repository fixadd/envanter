from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from models import (
    StockLog,
    ScrapPrinter,
    PrinterHistory,
    Inventory,
    InventoryLog,
)

router = APIRouter()

def get_templates(request: Request):
    return request.app.state.templates

@router.get("/scrap/detail/{id}", response_class=HTMLResponse)
def scrap_detail(id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(StockLog, id)
    templates = get_templates(request)
    return templates.TemplateResponse("partials/scrap_detail.html", {"request": request, "row": row})


@router.get("/scrap/printer/{printer_id}", response_class=HTMLResponse)
def scrap_printer_detail(printer_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.query(ScrapPrinter).filter(ScrapPrinter.printer_id == printer_id).first()
    if not row:
        raise HTTPException(404, "Kayıt bulunamadı")
    logs = (
        db.query(PrinterHistory)
        .filter(PrinterHistory.printer_id == printer_id)
        .order_by(PrinterHistory.created_at.desc())
        .all()
    )
    templates = get_templates(request)
    return templates.TemplateResponse(
        "partials/scrap_printer_detail.html",
        {"request": request, "row": row, "logs": logs},
    )


@router.get("/scrap/inventory/{inv_id}", response_class=HTMLResponse)
def scrap_inventory_detail(inv_id: int, request: Request, db: Session = Depends(get_db)):
    inv = db.get(Inventory, inv_id)
    if not inv:
        raise HTTPException(404, "Kayıt bulunamadı")
    logs = (
        db.query(InventoryLog)
        .filter(InventoryLog.inventory_id == inv_id)
        .order_by(InventoryLog.created_at.desc())
        .all()
    )
    templates = get_templates(request)
    return templates.TemplateResponse(
        "partials/scrap_inventory_detail.html",
        {"request": request, "inv": inv, "logs": logs},
    )
