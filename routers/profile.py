# routers/profile.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from security import SessionUser, current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def profile_home(request: Request, user: SessionUser = Depends(current_user)):
    first_name = ""
    last_name = ""
    if user.full_name:
        parts = user.full_name.split(" ", 1)
        first_name = parts[0]
        if len(parts) > 1:
            last_name = parts[1]
    return templates.TemplateResponse(
        "profile/index.html",
        {
            "request": request,
            "user": user,
            "first_name": first_name,
            "last_name": last_name,
        },
    )
