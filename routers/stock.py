# routers/stock.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def stock_home(request: Request):
    return templates.TemplateResponse("stock/list.html", {"request": request})

@router.get("/receipt/in", response_class=HTMLResponse)
async def receipt_in(request: Request):
    return templates.TemplateResponse("stock/receipt_in.html", {"request": request})

@router.get("/receipt/out", response_class=HTMLResponse)
async def receipt_out(request: Request):
    return templates.TemplateResponse("stock/receipt_out.html", {"request": request})

@router.get("/count", response_class=HTMLResponse)
async def stock_count(request: Request):
    return templates.TemplateResponse("stock/count.html", {"request": request})
