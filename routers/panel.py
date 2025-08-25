from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, sub: str = "urun"):
    return request.app.state.templates.TemplateResponse(
        "admin_panel.html",
        {"request": request, "sub": sub}
    )
