from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, tab: str = "admin", sub: str = "urun"):
    return request.app.state.templates.TemplateResponse(
        "panel_tabs.html", {"request": request, "page": "admin", "tab": tab, "sub": sub}
    )

@router.get("/talep", response_class=HTMLResponse)
async def talep_panel(request: Request, tab: str = "talep", sub: str = "aktif"):
    return request.app.state.templates.TemplateResponse(
        "panel_tabs.html", {"request": request, "page": "talep", "tab": tab, "sub": sub}
    )
