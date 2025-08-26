# routers/integrations.py
import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from ldap3 import Connection, Server
from dotenv import set_key

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def integrations_home(request: Request):
    return templates.TemplateResponse("integrations/index.html", {"request": request})


@router.get("/ldap", response_class=HTMLResponse)
async def ldap_users(request: Request):
    server_uri = os.getenv("LDAP_SERVER")
    bind_dn = os.getenv("LDAP_BIND_DN")
    bind_password = os.getenv("LDAP_BIND_PASSWORD")
    base_dn = os.getenv("LDAP_BASE_DN")
    users: list[dict[str, str]] = []
    error = None
    if server_uri and bind_dn and bind_password and base_dn:
        try:
            server = Server(server_uri)
            conn = Connection(
                server, user=bind_dn, password=bind_password, auto_bind=True
            )
            conn.search(base_dn, "(objectClass=person)", attributes=["cn", "mail"])
            for entry in conn.entries:
                users.append(
                    {
                        "cn": entry.cn.value,
                        "mail": entry.mail.value if "mail" in entry else "",
                    }
                )
            conn.unbind()
        except Exception as exc:  # pragma: no cover - best effort
            error = str(exc)
    else:
        error = "LDAP ayarları eksik"
    return templates.TemplateResponse(
        "integrations/ldap.html",
        {"request": request, "users": users, "error": error},
    )


@router.get("/ldap/settings", response_class=HTMLResponse)
async def ldap_settings_form(request: Request):
    return templates.TemplateResponse(
        "integrations/ldap_settings.html",
        {
            "request": request,
            "server": os.getenv("LDAP_SERVER", ""),
            "bind_dn": os.getenv("LDAP_BIND_DN", ""),
            "bind_password": os.getenv("LDAP_BIND_PASSWORD", ""),
            "base_dn": os.getenv("LDAP_BASE_DN", ""),
            "message": None,
            "error": None,
        },
    )


@router.post("/ldap/settings", response_class=HTMLResponse)
async def ldap_settings_save(
    request: Request,
    server: str = Form(""),
    bind_dn: str = Form(""),
    bind_password: str = Form(""),
    base_dn: str = Form(""),
    action: str = Form(""),
):
    message = None
    error = None

    # Attempt connection when testing or saving
    if action in {"test", "save"}:
        try:
            server_obj = Server(server)
            conn = Connection(
                server_obj, user=bind_dn, password=bind_password, auto_bind=True
            )
            conn.unbind()
            message = "Bağlantı başarılı"
        except Exception as exc:  # pragma: no cover - best effort
            error = str(exc)

    # Persist settings if requested and connection succeeded
    if action == "save" and not error:
        env_path = ".env"
        set_key(env_path, "LDAP_SERVER", server)
        set_key(env_path, "LDAP_BIND_DN", bind_dn)
        set_key(env_path, "LDAP_BIND_PASSWORD", bind_password)
        set_key(env_path, "LDAP_BASE_DN", base_dn)
        os.environ.update(
            {
                "LDAP_SERVER": server,
                "LDAP_BIND_DN": bind_dn,
                "LDAP_BIND_PASSWORD": bind_password,
                "LDAP_BASE_DN": base_dn,
            }
        )
        return RedirectResponse("/integrations/ldap", status_code=303)

    return templates.TemplateResponse(
        "integrations/ldap_settings.html",
        {
            "request": request,
            "server": server,
            "bind_dn": bind_dn,
            "bind_password": bind_password,
            "base_dn": base_dn,
            "message": message,
            "error": error,
        },
    )
