from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.exc import InvalidHash
from starlette import status as st_status
from starlette.middleware.sessions import SessionMiddleware

from app.core.security import hash_password, pwd_context, verify_password
from app.db.init import bootstrap_schema, init_db
from app.web import register_web_routes
from utils.template_filters import register_filters

load_dotenv()


# --- Secrets & Config ---------------------------------------------------------
SESSION_SECRET_FILE = Path(__file__).resolve().parent.parent / ".session_secret"


def _read_persisted_secret() -> str | None:
    """Return a previously generated session secret if available."""

    try:
        data = SESSION_SECRET_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError:
        return None

    if len(data) >= 32:
        return data
    return None


def _persist_secret(value: str) -> None:
    """Persist the generated secret to disk for multi-worker reuse."""

    try:
        SESSION_SECRET_FILE.write_text(value, encoding="utf-8")
        try:
            SESSION_SECRET_FILE.chmod(0o600)
        except OSError:
            # Best-effort; lack of chmod support (e.g. on Windows) shouldn't fail startup.
            pass
    except OSError:
        # Persistence is best-effort; continue with in-memory secret if writing fails.
        pass


def _load_session_secret() -> str:
    """Return a session secret, generating a transient one if necessary."""

    secret = os.getenv("SESSION_SECRET")
    if secret and len(secret) >= 32:
        return secret

    persisted = _read_persisted_secret()
    if persisted:
        if secret and len(secret) < 32:
            print(
                "WARNING: SESSION_SECRET is shorter than 32 characters; "
                "using stored fallback from .session_secret file."
            )
        else:
            print(
                "WARNING: SESSION_SECRET environment variable is not set. "
                "Using previously generated value from .session_secret file."
            )
        os.environ.setdefault("SESSION_SECRET", persisted)
        return persisted

    if secret:
        print(
            "WARNING: SESSION_SECRET is shorter than 32 characters; "
            "generating and persisting a temporary value for development/test runs."
        )
    else:
        print(
            "WARNING: SESSION_SECRET environment variable is not set. "
            "Generating and persisting a temporary value for development/test runs."
        )

    generated = secrets.token_urlsafe(32)
    _persist_secret(generated)
    os.environ.setdefault("SESSION_SECRET", generated)
    return generated


SESSION_SECRET = _load_session_secret()

DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")
DEFAULT_ADMIN_FULLNAME = os.getenv("DEFAULT_ADMIN_FULLNAME", "Sistem Yöneticisi")
if not DEFAULT_ADMIN_PASSWORD:
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_DEV_PASSWORD", "admin123")
    print(
        "WARNING: DEFAULT_ADMIN_PASSWORD environment variable is not set. "
        "Using the development default password 'admin123'. "
        "Set DEFAULT_ADMIN_PASSWORD in production environments."
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


def _extract_error_message(detail: object) -> str:
    """Create a human readable message from various HTTPException.detail shapes."""

    if detail is None:
        return "Beklenmeyen bir hata oluştu."

    if isinstance(detail, str):
        text = detail.strip()
        return text or "Beklenmeyen bir hata oluştu."

    if isinstance(detail, dict):
        for key in ("message", "detail", "error", "msg"):
            value = detail.get(key)
            if value:
                return _extract_error_message(value)
        return "Beklenmeyen bir hata oluştu."

    if isinstance(detail, (list, tuple)):
        rendered = [_extract_error_message(item) for item in detail if item is not None]
        return ", ".join(filter(None, rendered)) or "Beklenmeyen bir hata oluştu."

    return str(detail)


def _resolve_error_title(status_code: int | None) -> str:
    """Return a friendly title based on HTTP status code."""

    mapping = {
        st_status.HTTP_400_BAD_REQUEST: "Geçersiz işlem",
        st_status.HTTP_401_UNAUTHORIZED: "Oturum gerekli",
        st_status.HTTP_403_FORBIDDEN: "Erişim reddedildi",
        st_status.HTTP_404_NOT_FOUND: "Sayfa bulunamadı",
        st_status.HTTP_500_INTERNAL_SERVER_ERROR: "Sunucu hatası",
    }
    return mapping.get(status_code, "Bir sorun oluştu")


def _safe_back_url(request: Request) -> str:
    referer = request.headers.get("referer", "")
    if not referer:
        return "/"
    try:
        parsed = urlparse(referer)
    except ValueError:
        return "/"

    if parsed.netloc and parsed.netloc != request.url.netloc:
        return "/"

    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"
    return path


@app.exception_handler(HTTPException)
async def redirect_on_auth(request: Request, exc: HTTPException):
    """Handle redirects and render friendly HTML errors for browser requests."""

    if isinstance(exc.detail, str) and exc.detail.startswith("redirect:/"):
        url = exc.detail.split(":", 1)[1]
        return RedirectResponse(url=url, status_code=st_status.HTTP_303_SEE_OTHER)

    accepts = (request.headers.get("accept") or "").lower()
    wants_html = "text/html" in accepts
    is_api_request = (
        request.url.path.startswith("/api") or "application/json" in accepts
    )

    if wants_html and not is_api_request:
        templates: Jinja2Templates = request.app.state.templates
        message = _extract_error_message(exc.detail)
        title = _resolve_error_title(exc.status_code)
        context = {
            "request": request,
            "status_code": exc.status_code or st_status.HTTP_500_INTERNAL_SERVER_ERROR,
            "error_title": title,
            "error_message": message,
            "back_url": _safe_back_url(request),
        }
        status_code = exc.status_code or st_status.HTTP_500_INTERNAL_SERVER_ERROR
        return templates.TemplateResponse(
            "error_modal.html", context, status_code=status_code
        )

    # Delegate to FastAPI's standard HTTP exception handler for API requests
    # so the appropriate status code (e.g. 404) is returned as JSON.
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
        existing = (
            db.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
        )
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
