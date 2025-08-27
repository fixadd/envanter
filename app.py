from __future__ import annotations
import os, secrets
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette import status as st_status
from sqlalchemy.orm import Session

from models import init_db
from db_bootstrap import bootstrap_schema
from auth import (
    get_db,
    get_user_by_username,
    get_user_by_id,
    verify_password,
    hash_password,
)
from routers import (
    home,
    inventory as inventory_router,
    license as license_router,
    printers as printers_router,
    printers_scrap_list,
    catalog as catalog_router,
    requests as reqs,
    stock,
    trash,
    profile,
    logs,
    refdata,
    panel as panel_router,
)
from routers.lookup import router as lookup_router
from routers.picker import router as picker_router
from routers.api import router as api_router
from routes.admin import router as admin_router
from security import current_user, require_roles

load_dotenv()
bootstrap_schema()

# --- Secrets & Config ---------------------------------------------------------
SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET or len(SESSION_SECRET) < 32:
    # Geliştirme kolaylığı için otomatik üret; üretimde .env zorunlu
    SESSION_SECRET = secrets.token_urlsafe(48)
    print(
        "WARNING: SESSION_SECRET .env'de bulunamadı ya da kısa; geçici anahtar üretildi. "
        "Üretimde sabit ve 32+ karakter kullanın!"
    )

DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_FULLNAME = os.getenv("DEFAULT_ADMIN_FULLNAME", "Sistem Yöneticisi")

# --- App & Middleware ---------------------------------------------------------
app = FastAPI(title="Envanter Takip – Login")

@app.exception_handler(HTTPException)
async def redirect_on_auth(request, exc: HTTPException):
    """Handle custom redirect signals while delegating other errors.

    `security.py` may raise an ``HTTPException`` whose ``detail`` begins with
    ``"redirect:/"`` to indicate the user should be redirected. For all other
    ``HTTPException`` instances we fall back to FastAPI's default behaviour
    instead of re-raising, which previously resulted in a 500 response.
    """

    if isinstance(exc.detail, str) and exc.detail.startswith("redirect:/"):
        url = exc.detail.split(":", 1)[1]
        return RedirectResponse(url=url, status_code=st_status.HTTP_303_SEE_OTHER)

    # Delegate to FastAPI's standard HTTP exception handler for all other
    # errors so the appropriate status code (e.g. 404) is returned.
    return await http_exception_handler(request, exc)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=False,
)

# Statik dosyalar ve şablonlar
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.state.templates = templates

# --- Routers (korumalı) -------------------------------------------------------
app.include_router(home.router, prefix="", dependencies=[Depends(current_user)])
app.include_router(panel_router.router, dependencies=[Depends(current_user)])
app.include_router(inventory_router.router, dependencies=[Depends(current_user)])
app.include_router(license_router.router, dependencies=[Depends(current_user)])
app.include_router(printers_router.router, dependencies=[Depends(current_user)])
app.include_router(printers_scrap_list.router, dependencies=[Depends(current_user)])
app.include_router(catalog_router.router, dependencies=[Depends(current_user)])
app.include_router(reqs.router, prefix="/requests", tags=["Requests"], dependencies=[Depends(current_user)])
app.include_router(stock.router, dependencies=[Depends(current_user)])
app.include_router(trash.router, prefix="/trash", tags=["Trash"], dependencies=[Depends(current_user)])
app.include_router(profile.router, prefix="/profile", tags=["Profile"], dependencies=[Depends(current_user)])
app.include_router(api_router)
app.include_router(picker_router)
app.include_router(lookup_router)
app.include_router(refdata.router, dependencies=[Depends(current_user)])

@app.get("/licenses", include_in_schema=False)
def licenses_list_alias(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    return license_router.license_list(request, db, user)

@app.get("/licenses/{lic_id}", include_in_schema=False)
def licenses_detail_alias(lic_id: int, request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    return license_router.license_detail(lic_id, request, db)

# Sadece admin
app.include_router(logs.router, prefix="/logs", tags=["Logs"], dependencies=[Depends(require_roles("admin"))])
app.include_router(admin_router, dependencies=[Depends(require_roles("admin"))])

# --- Startup: DB init & default admin ----------------------------------------
@app.on_event("startup")
def on_startup():
    from models import SessionLocal, User
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
        if not existing:
            u = User(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                full_name=DEFAULT_ADMIN_FULLNAME,
            )
            db.add(u)
            db.commit()
            print(f"[*] Varsayılan admin oluşturuldu: {DEFAULT_ADMIN_USERNAME}")
    finally:
        db.close()

# --- CSRF yardımcıları --------------------------------------------------------
def _ensure_csrf(request: Request) -> str:
    token = secrets.token_urlsafe(32)
    request.session["csrf_token"] = token
    return token

def _check_csrf(request: Request, token_from_form: Optional[str]) -> bool:
    return bool(token_from_form) and request.session.get("csrf_token") == token_from_form

# --- Login/Logout -------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    # Zaten girişliyse yönlendir
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    csrf_token = _ensure_csrf(request)
    saved_username = request.cookies.get("saved_username", "")
    saved_password = request.cookies.get("saved_password", "")
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "csrf_token": csrf_token,
            "error": None,
            "saved_username": saved_username,
            "saved_password": saved_password,
        },
    )

@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember: Optional[str] = Form(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    saved_username = request.cookies.get("saved_username", "")
    saved_password = request.cookies.get("saved_password", "")
    if not _check_csrf(request, csrf_token):
        csrf_token = _ensure_csrf(request)
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "csrf_token": csrf_token,
                "error": "Oturum süresi doldu. Lütfen tekrar deneyin.",
                "saved_username": saved_username,
                "saved_password": saved_password,
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
                "saved_password": saved_password,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Başarılı giriş
    request.session["user_id"] = user.id
    request.session["user_name"] = user.full_name or user.username
    request.session["user_role"] = getattr(user, "role", "")
    _ensure_csrf(request)  # token yenile
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    if remember:
        response.set_cookie("saved_username", username, max_age=60 * 60 * 24 * 30)
        response.set_cookie("saved_password", password, max_age=60 * 60 * 24 * 30)
    else:
        response.delete_cookie("saved_username")
        response.delete_cookie("saved_password")
    return response

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
