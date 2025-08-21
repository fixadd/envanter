# routers/admin.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def admin_home(request: Request):
    return templates.TemplateResponse("admin/users.html", {"request": request})

@router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    return templates.TemplateResponse("admin/users.html", {"request": request})

@router.get("/taxonomies", response_class=HTMLResponse)
async def admin_taxonomies(request: Request):
    return templates.TemplateResponse("admin/taxonomies.html", {"request": request})

@router.get("/integrations", response_class=HTMLResponse)
async def admin_integrations(request: Request):
    return templates.TemplateResponse("admin/integrations.html", {"request": request})

@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(request: Request):
    return templates.TemplateResponse("admin/settings.html", {"request": request})
