# routers/inventory.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def list_inventory(request: Request):
    return templates.TemplateResponse("inventory/list.html", {"request": request})

@router.get("/{item_id}", response_class=HTMLResponse)
async def inventory_detail(item_id: int, request: Request):
    return templates.TemplateResponse("inventory/detail.html", {"request": request, "item_id": item_id})

@router.get("/{item_id}/maintenance", response_class=HTMLResponse)
async def inventory_maintenance(item_id: int, request: Request):
    return templates.TemplateResponse("inventory/maintenance.html", {"request": request, "item_id": item_id})

@router.get("/{item_id}/history", response_class=HTMLResponse)
async def inventory_history(item_id: int, request: Request):
    return templates.TemplateResponse("inventory/history.html", {"request": request, "item_id": item_id})

@router.get("/{item_id}/edit", response_class=HTMLResponse)
async def inventory_edit(item_id: int, request: Request):
    return templates.TemplateResponse("inventory/edit.html", {"request": request, "item_id": item_id})
