# routers/profile.py
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import User
from security import SessionUser, current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def profile_home(
    request: Request,
    db: Session = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    u = db.get(User, user.id)
    first_name = u.first_name if u and u.first_name else ""
    last_name = u.last_name if u and u.last_name else ""
    theme = u.theme if u and getattr(u, "theme", None) else "default"
    animation = u.animation if u and getattr(u, "animation", None) else "none"
    return templates.TemplateResponse(
        "profile/index.html",
        {
            "request": request,
            "user": user,
            "first_name": first_name,
            "last_name": last_name,
            "theme": theme,
            "animation": animation,
        },
    )


@router.post("/theme")
async def update_theme(
    request: Request,
    theme: str = Form(...),
    animation: str = Form(...),
    db: Session = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    u = db.get(User, user.id)
    if u:
        u.theme = theme
        u.animation = animation
        db.add(u)
        db.commit()
        request.session["user_theme"] = theme
        request.session["user_anim"] = animation
    return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
