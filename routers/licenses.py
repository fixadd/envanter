# routers/licenses.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def list_licenses(request: Request):
    return templates.TemplateResponse("licenses/list.html", {"request": request})

@router.get("/assign", response_class=HTMLResponse)
async def assign_license(request: Request):
    return templates.TemplateResponse("licenses/assign.html", {"request": request})
