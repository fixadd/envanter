# routers/trash.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def trash_list(request: Request):
    return templates.TemplateResponse("trash/list.html", {"request": request})
