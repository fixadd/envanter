from fastapi import APIRouter, Depends, Request, HTTPException, Form
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_, asc
from typing import Optional
from types import SimpleNamespace

from models import Lookup
from auth import get_db, hash_password

try:
    from models import User
except Exception as e:
    raise RuntimeError("User modeli bulunamadı; models.py içindeki User sınıfını kullanın.") from e

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("", response_class=HTMLResponse)
def admin_panel(request: Request, q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(User)
    if q:
        q_like = f"%{q}%"
        query = query.filter(
            or_(
                User.username.ilike(q_like),
                User.full_name.ilike(q_like),
            )
        )
    db_users = query.order_by(asc(User.id)).all()

    users = []
    for u in db_users:
        first_name = ""
        last_name = ""
        if u.full_name:
            parts = u.full_name.split(" ", 1)
            first_name = parts[0]
            if len(parts) > 1:
                last_name = parts[1]
        users.append(
            SimpleNamespace(
                id=u.id,
                username=u.username,
                first_name=first_name,
                last_name=last_name,
                email=getattr(u, "email", "") or "",
                is_admin=1 if getattr(u, "role", "") == "admin" else 0,
            )
        )

    CATS = [
        "kullanim_alani",
        "lisans_adi",
        "fabrika",
        "donanim_tipi",
        "marka",
        "model",
    ]
    lookups = {
        c: db.query(Lookup).filter(Lookup.category == c).order_by(asc(Lookup.value)).all()
        for c in CATS
    }

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "users": users,
            "q": q or "",
            "lookups": lookups,
            "CATS": CATS,
        },
    )


@router.post("/users/create")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    is_admin: Optional[bool] = Form(False),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "Bu kullanıcı adı zaten mevcut.")
    full_name = f"{first_name} {last_name}".strip()
    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        email=email,
        role="admin" if is_admin else "user",
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/users/{user_id}/update")
def update_user(
    user_id: int,
    username: str = Form(...),
    password: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    is_admin: Optional[bool] = Form(False),
    db: Session = Depends(get_db),
):
    # SQLAlchemy 2.0 stili
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadı.")

    if username != user.username and db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "Bu kullanıcı adı zaten kullanılıyor.")

    user.username = username
    user.full_name = f"{first_name} {last_name}".strip()
    user.role = "admin" if is_admin else "user"
    user.email = email
    if password.strip():
        user.password_hash = hash_password(password)

    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/users/{user_id}/delete")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadı.")
    if user.username.lower() == "admin":
        raise HTTPException(400, "Admin hesabı silinemez.")
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/lookups/add")
def add_lookup(
    category: str = Form(...),
    value: str = Form(...),
    who: str = Form(""),
    db: Session = Depends(get_db),
):
    value = value.strip()
    if not value:
        raise HTTPException(400, "Değer boş olamaz.")
    exists = db.query(Lookup).filter(Lookup.category == category, Lookup.value == value).first()
    if exists:
        raise HTTPException(400, "Bu değer zaten var.")
    db.add(Lookup(category=category, value=value, created_by=who))
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/lookups/{lookup_id}/delete")
def delete_lookup(lookup_id: int, db: Session = Depends(get_db)):
    lk = db.get(Lookup, lookup_id)
    if not lk:
        raise HTTPException(404, "Kayıt bulunamadı.")
    db.delete(lk)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

