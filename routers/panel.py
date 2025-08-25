from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

# /admin rotasının admin router'ı tarafından
# kullanılabilmesi için bu paneli farklı bir
# adrese taşıyoruz.
@router.get("/panel", response_class=HTMLResponse)
async def admin_panel(request: Request, sub: str = "urun"):
    return request.app.state.templates.TemplateResponse(
        "admin_panel.html",
        {"request": request, "sub": sub}
    )
