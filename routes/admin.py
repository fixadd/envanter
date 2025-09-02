from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models import User, Lookup, Setting
import models
from database import get_db
from fastapi.templating import Jinja2Templates
from auth import hash_password
from security import SessionUser, current_user

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse, name="admin_index")
def admin_index(request: Request, tab: str = "kullanici", q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(User)
    if q:
        like = f"%{q}%"
        filters = [User.username.ilike(like)]
        if hasattr(User, "full_name"):
            filters.append(User.full_name.ilike(like))
        if hasattr(User, "first_name"):
            filters.append(User.first_name.ilike(like))
        if hasattr(User, "last_name"):
            filters.append(User.last_name.ilike(like))
        if hasattr(User, "email"):
            filters.append(User.email.ilike(like))
        query = query.filter(or_(*filters))
    users = query.order_by(User.username.asc()).all()

    def get(type_):
        return (
            db.query(Lookup)
            .filter(Lookup.type == type_)
            .order_by(Lookup.value.asc())
            .all()
        )

    ctx = {
        "request": request,
        "users": users,
        "q": q,
        "lookup_kullanim_alanlari": get("kullanim_alani"),
        "lookup_lisans_adlari": get("lisans_adi"),
        "lookup_fabrikalar": get("fabrika"),
        "lookup_donanim_tipleri": get("donanim_tipi"),
        "lookup_markalar": get("marka"),
        "lookup_modeller": get("model"),
    }
    ctx["tab"] = tab
    return templates.TemplateResponse("admin/index.html", ctx)

@router.post("/users/create")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    is_admin: bool = Form(False),
    db: Session = Depends(get_db),
):
    u = User(
        username=username,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        full_name=f"{first_name} {last_name}".strip(),
        email=email or None,
        role="admin" if is_admin else "user",
    )
    db.add(u)
    db.commit()
    return RedirectResponse(url="/admin#users", status_code=303)

@router.post("/products/create")
def create_product(
    donanim_tipi: str = Form(...),
    marka: str = Form(""),
    model: str = Form(""),
    kullanim_alani: str = Form(""),
    lisans_adi: str = Form(""),
    fabrika: str = Form(""),
    db: Session = Depends(get_db),
):
    # Uygun veri modeli seç (Product tanımlı değilse Inventory kullan)
    model_cls = getattr(models, "Product", models.Inventory)

    if not donanim_tipi:
        raise HTTPException(status_code=400, detail="Donanım tipi gerekli")

    data = {
        "donanim_tipi": donanim_tipi,
        "marka": marka or None,
        "model": model or None,
        "kullanim_alani": kullanim_alani or None,
        "fabrika": fabrika or None,
    }
    if hasattr(model_cls, "__table__") and "lisans_adi" in model_cls.__table__.columns:
        data["lisans_adi"] = lisans_adi or None

    item = model_cls(**data)
    db.add(item)
    db.commit()
    return RedirectResponse(url="/admin#products", status_code=303)

@router.post("/users/{uid}/edit")
def user_edit_post(
    uid: int,
    username: str = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    is_admin: bool = Form(False),
    db: Session = Depends(get_db),
):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    u.username = username
    u.first_name = first_name
    u.last_name = last_name
    u.full_name = f"{first_name} {last_name}".strip()
    u.email = email or None
    u.role = "admin" if is_admin else "user"
    if password:
        u.password_hash = hash_password(password)
    db.add(u)
    db.commit()
    return RedirectResponse(url="/admin#users", status_code=303)


@router.post("/users/{uid}/delete")
def user_delete(
    uid: int,
    user: SessionUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    target = db.get(User, uid)
    if not target:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    if target.username.lower() == "admin":
        raise HTTPException(403, "Admin silinemez")
    if user.username.lower() != "admin" and target.role == "admin":
        raise HTTPException(403, "Adminler birbirini silemez")
    db.delete(target)
    db.commit()
    return RedirectResponse(url="/admin#users", status_code=303)


@router.get("/connections/ldap", response_class=HTMLResponse)
def ldap_get(request:Request, db:Session=Depends(get_db)):
    def g(k):
        s = db.query(Setting).filter_by(key=k).first()
        return s.value if s else ""
    ctx = {
        "request":request,
        "host": g("ldap.host"),
        "base_dn": g("ldap.base_dn"),
        "bind_dn": g("ldap.bind_dn"),
        "bind_password": g("ldap.bind_password"),
        "use_ssl": g("ldap.use_ssl"),
    }
    return templates.TemplateResponse("admin_ldap.html", ctx)

@router.post("/connections/ldap")
def ldap_post(host:str=Form(""), base_dn:str=Form(""), bind_dn:str=Form(""), bind_password:str=Form(""), use_ssl:str=Form("0"), db:Session=Depends(get_db)):
    for k,v in [
        ("ldap.host",host), ("ldap.base_dn",base_dn), ("ldap.bind_dn",bind_dn),
        ("ldap.bind_password",bind_password), ("ldap.use_ssl",use_ssl)
    ]:
        s = db.query(Setting).filter_by(key=k).first()
        if not s: s = Setting(key=k, value=v); db.add(s)
        else: s.value = v
    db.commit()
    return RedirectResponse(url="/admin/connections/ldap", status_code=303)
