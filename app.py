from __future__ import annotations
import os, secrets
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from fastapi.responses import RedirectResponse
from routers import home, inventory, licenses, accessories, printers, requests as reqs, stock, trash, profile, admin, integrations, logs
from security import current_user, require_roles
from starlette import status as st_status


from models import init_db
from auth import get_db, get_user_by_username, get_user_by_id, verify_password, hash_password


load_dotenv()


SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET or len(SESSION_SECRET) < 32:
# Geliştirme kolaylığı için otomatik üret; üretimde .env zorunlu
 SESSION_SECRET = secrets.token_urlsafe(48)
 print("WARNING: SESSION_SECRET .env'de bulunamadı; geçici bir anahtar üretildi. Üretimde sabit bir gizli anahtar kullanın!")


DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_FULLNAME = os.getenv("DEFAULT_ADMIN_FULLNAME", "Sistem Yöneticisi")


app = FastAPI(title="Envanter Takip – Login")
@app.exception_handler(HTTPException)
async def redirect_on_auth(request, exc: HTTPException):
    # security.py'den gelen "redirect:/..." sinyalini işle
    if isinstance(exc.detail, str) and exc.detail.startswith("redirect:/"):
        url = exc.detail.split(":", 1)[1]
        return RedirectResponse(url=url, status_code=st_status.HTTP_303_SEE_OTHER)
    raise exc
# Korumalı modüller
app.include_router(home.router, prefix="", dependencies=[Depends(current_user)])
app.include_router(inventory.router, prefix="/inventory", tags=["Inventory"], dependencies=[Depends(current_user)])
app.include_router(licenses.router, prefix="/licenses", tags=["Licenses"], dependencies=[Depends(current_user)])
app.include_router(accessories.router, prefix="/accessories", tags=["Accessories"], dependencies=[Depends(current_user)])
app.include_router(printers.router, prefix="/printers", tags=["Printers"], dependencies=[Depends(current_user)])
app.include_router(reqs.router, prefix="/requests", tags=["Requests"], dependencies=[Depends(current_user)])
app.include_router(stock.router, prefix="/stock", tags=["Stock"], dependencies=[Depends(current_user)])
app.include_router(trash.router, prefix="/trash", tags=["Trash"], dependencies=[Depends(current_user)])
app.include_router(profile.router, prefix="/profile", tags=["Profile"], dependencies=[Depends(current_user)])
app.include_router(integrations.router, prefix="/integrations", tags=["Integrations"], dependencies=[Depends(current_user)])

# Sadece admin
app.include_router(logs.router, prefix="/logs", tags=["Logs"], dependencies=[Depends(require_roles("admin"))])
app.include_router(admin.router, prefix="/admin", tags=["Admin"], dependencies=[Depends(require_roles("admin"))])

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=60*60*8, same_site="lax", https_only=False)


# Statik dosyalar ve şablonlar
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")




@app.on_event("startup")
def on_startup():
# DB'yi oluştur ve default admin ekle
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
print(f"[*] Varsayılan admin oluşturuldu: {DEFAULT_ADMIN_USERNAME} / (parolayı .env'den bakın)")
finally:
db.close()




def _ensure_csrf(request: Request) -> str:
token = secrets.token_urlsafe(32)
request.session["csrf_token"] = token
return token




def _check_csrf(request: Request, token_from_form: Optional[str]) -> bool:
return token_from_form and request.session.get("csrf_token") == token_from_form




@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
# Zaten girişliyse yönlendir
if request.session.get("user_id"):
return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
csrf_token = _ensure_csrf(request)
return templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token, "error": None})




@app.post("/login", response_class=HTMLResponse)
async def login_submit(
request: Request,
)