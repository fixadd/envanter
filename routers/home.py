# routers/home.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = {
        "envanter_sayisi": 0,
        "lisans_sayisi": 0,
        "bekleyen_talep": 0,
        "son_islemler": [],
    }
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "stats": stats}
    )
