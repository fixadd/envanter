# routers/integrations.py
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ldap3 import Connection, Server

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
