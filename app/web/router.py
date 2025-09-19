from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth import get_user_by_username
from database import get_db
from app.core.security import verify_password
from routers import (
    catalog as catalog_router,
    home as home_router,
    inventory as inventory_router,
    license as license_router,
    panel as panel_router,
    printers as printers_router,
    printers_scrap_list,
    profile,
    refdata,
    requests as requests_router,
    stock,
    trash,
    logs,
)
from routers.lookup import router as lookup_router
from routers.picker import router as picker_router
from routers.api import router as api_router
from routes.admin import router as admin_router
from routes.scrap import router as scrap_router
from routes.talepler import router as talepler_router
from routers.talep import router as talep_router
from security import current_user, require_roles
from utils.template_filters import register_filters

router = APIRouter()


def _get_templates(request: Request) -> Jinja2Templates:
    templates = getattr(request.app.state, "templates", None)
    if templates is None:
        templates = register_filters(Jinja2Templates(directory="templates"))
        request.app.state.templates = templates
    return templates


def _ensure_csrf(request: Request) -> str:
    token = secrets.token_urlsafe(32)
    request.session["csrf_token"] = token
    return token


def _check_csrf(request: Request, token_from_form: Optional[str]) -> bool:
    return bool(token_from_form) and request.session.get("csrf_token") == token_from_form


@router.get("/", include_in_schema=False)
def root(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    csrf_token = _ensure_csrf(request)
    saved_username = request.cookies.get("saved_username", "")
    templates = _get_templates(request)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "csrf_token": csrf_token,
            "error": None,
            "saved_username": saved_username,
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember: Optional[str] = Form(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    saved_username = request.cookies.get("saved_username", "")
    templates = _get_templates(request)

    if not _check_csrf(request, csrf_token):
        csrf_token = _ensure_csrf(request)
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "error": "Oturum süresi doldu. Lütfen tekrar deneyin.",
                "saved_username": saved_username,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = get_user_by_username(db, username.strip())
    if not user or not verify_password(password, user.password_hash):
        csrf_token = _ensure_csrf(request)
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "error": "Kullanıcı adı veya parola hatalı.",
                "saved_username": saved_username,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    request.session["user_id"] = user.id
    request.session["user_name"] = user.full_name or user.username
    request.session["user_role"] = getattr(user, "role", "")
    request.session["user_theme"] = getattr(user, "theme", "default")
    request.session["user_anim"] = getattr(user, "animation", "none")
    _ensure_csrf(request)

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    if remember:
        response.set_cookie("saved_username", username, max_age=60 * 60 * 24 * 30)
    else:
        response.delete_cookie("saved_username")
    return response


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/licenses", include_in_schema=False)
def licenses_list_alias(
    request: Request, db: Session = Depends(get_db), user=Depends(current_user)
):
    return license_router.license_list(request, db, user)


@router.get("/licenses/{lic_id}", include_in_schema=False)
def licenses_detail_alias(
    lic_id: int, request: Request, db: Session = Depends(get_db), user=Depends(current_user)
):
    return license_router.license_detail(lic_id, request, db)


@router.get("/licenses/{lic_id}/edit", include_in_schema=False)
def licenses_edit_alias(
    lic_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    return license_router.edit_license_form(lic_id, request, db)


@router.get("/licenses/{lic_id}/assign", include_in_schema=False)
def licenses_assign_alias(
    lic_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    return license_router.assign_license_form(lic_id, request, db, user)


@router.get("/licenses/{lic_id}/stock", include_in_schema=False)
def licenses_stock_alias(
    lic_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    return license_router.stock_license(lic_id, db, user)


router.include_router(
    home_router.router, dependencies=[Depends(current_user)]
)
router.include_router(
    panel_router.router, dependencies=[Depends(current_user)]
)
router.include_router(
    inventory_router.router, dependencies=[Depends(current_user)]
)
router.include_router(
    license_router.router, dependencies=[Depends(current_user)]
)
router.include_router(
    printers_scrap_list.router, dependencies=[Depends(current_user)]
)
router.include_router(
    printers_router.router, dependencies=[Depends(current_user)]
)
router.include_router(
    catalog_router.router, dependencies=[Depends(current_user)]
)
router.include_router(
    requests_router.router,
    prefix="/requests",
    tags=["Requests"],
    dependencies=[Depends(current_user)],
)
router.include_router(
    stock.router, dependencies=[Depends(current_user)]
)
router.include_router(
    stock.api_router, dependencies=[Depends(current_user)]
)
router.include_router(
    scrap_router, dependencies=[Depends(current_user)]
)
router.include_router(
    talepler_router, dependencies=[Depends(current_user)]
)
router.include_router(
    trash.router,
    prefix="/trash",
    tags=["Trash"],
    dependencies=[Depends(current_user)],
)
router.include_router(
    profile.router,
    prefix="/profile",
    tags=["Profile"],
    dependencies=[Depends(current_user)],
)
router.include_router(
    refdata.router, dependencies=[Depends(current_user)]
)
router.include_router(api_router)
router.include_router(picker_router)
router.include_router(lookup_router)
router.include_router(talep_router)
router.include_router(
    logs.router,
    prefix="/logs",
    tags=["Logs"],
    dependencies=[Depends(require_roles("admin"))],
)
router.include_router(
    admin_router, dependencies=[Depends(require_roles("admin"))]
)


def register_web_routes(app: FastAPI) -> None:
    """Tüm web router'larını FastAPI uygulamasına ekle."""

    app.include_router(router)
