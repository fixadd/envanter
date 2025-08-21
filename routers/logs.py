# routers/logs.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def logs_home(request: Request):
    return templates.TemplateResponse("logs/index.html", {"request": request})
