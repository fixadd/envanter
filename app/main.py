from __future__ import annotations

import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status as st_status
from starlette.middleware.sessions import SessionMiddleware

from app.core.security import hash_password
from app.db.init import bootstrap_schema, init_db
from app.web import register_web_routes
from utils.template_filters import register_filters

load_dotenv()

# --- Secrets & Config ---------------------------------------------------------
SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET or len(SESSION_SECRET) < 32:
    raise RuntimeError(
        "SESSION_SECRET environment variable must be defined and at least 32 characters long."
    )

DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")
DEFAULT_ADMIN_FULLNAME = os.getenv("DEFAULT_ADMIN_FULLNAME", "Sistem Yöneticisi")
_generated_admin_password: str | None = None
if not DEFAULT_ADMIN_PASSWORD:
    _generated_admin_password = secrets.token_urlsafe(20)
    DEFAULT_ADMIN_PASSWORD = _generated_admin_password
    print(
        "WARNING: DEFAULT_ADMIN_PASSWORD environment variable is not set. "
        "Generated a one-time password for the default admin user."
    )
# Varsayılan olarak geliştirme ortamına uygun olsun; üretimde .env ile true yapın
SESSION_HTTPS_ONLY = os.getenv("SESSION_HTTPS_ONLY", "false").lower() in (
    "1",
    "true",
    "t",
    "yes",
)
if not SESSION_HTTPS_ONLY:
    print(
        "WARNING: SESSION cookies are not marked secure; set SESSION_HTTPS_ONLY=true in production."
    )

# --- App & Middleware ---------------------------------------------------------
app = FastAPI(title="Envanter Takip – Login")


@app.exception_handler(HTTPException)
async def redirect_on_auth(request: Request, exc: HTTPException):
    """Handle custom redirect signals while delegating other errors."""

    if isinstance(exc.detail, str) and exc.detail.startswith("redirect:/"):
        url = exc.detail.split(":", 1)[1]
        return RedirectResponse(url=url, status_code=st_status.HTTP_303_SEE_OTHER)

    # Delegate to FastAPI's standard HTTP exception handler for all other
    # errors so the appropriate status code (e.g. 404) is returned.
    return await http_exception_handler(request, exc)


def _register_global_state() -> None:
    """Initialise shared application state such as templates."""

    templates = register_filters(Jinja2Templates(directory="templates"))
    app.state.templates = templates


app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=SESSION_HTTPS_ONLY,
)

# Statik dosyalar ve şablonlar
app.mount("/static", StaticFiles(directory="static"), name="static")
_register_global_state()
app.state.session_https_only = SESSION_HTTPS_ONLY

# Web router'ları ve HTML sayfaları
register_web_routes(app)


# --- Startup: DB init & default admin ----------------------------------------
@app.on_event("startup")
def on_startup():
    from models import SessionLocal, User

    # Ensure environment variables are available before running any migrations
    load_dotenv()
    bootstrap_schema()
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
            if _generated_admin_password:
                print(
                    "[*] Varsayılan admin için geçici parola: "
                    f"{_generated_admin_password}"
                )
    finally:
        db.close()
