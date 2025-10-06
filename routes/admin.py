from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
from auth import hash_password
from database import get_db
from models import Connection, Lookup, Setting, User
from security import SessionUser, current_user

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")


def _set_flash(
    request: Request | None,
    message: str,
    *,
    title: str | None = None,
    variant: str = "primary",
) -> None:
    if request is None:
        return
    request.session["_flash"] = {
        "message": message,
        "title": title,
        "variant": variant,
    }


def _error_response(
    request: Request | None,
    *,
    status_code: int,
    message: str,
    title: str,
    redirect_url: str = "/admin#users",
    variant: str = "danger",
):
    if request is None:
        raise HTTPException(status_code=status_code, detail=message)
    _set_flash(request, message, title=title, variant=variant)
    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("", response_class=HTMLResponse, name="admin_index")
def admin_index(
    request: Request,
    tab: str = "kullanici",
    q: str | None = None,
    db: Session = Depends(get_db),
):
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

    connections = db.query(Connection).order_by(Connection.name.asc()).all()

    def get(type_):
        return (
            db.query(Lookup)
            .filter(Lookup.type == type_)
            .order_by(Lookup.value.asc())
            .all()
        )

    flash = request.session.pop("_flash", None)

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
        "connections": connections,
        "flash": flash,
    }
    ctx["tab"] = tab
    return templates.TemplateResponse("admin/index.html", ctx)


def _normalize_user_fields(
    username: str,
    first_name: str,
    last_name: str,
    email: str,
) -> tuple[str, str, str, str | None]:
    normalized_username = username.strip()
    normalized_first = first_name.strip()
    normalized_last = last_name.strip()
    normalized_email = email.strip()
    if not normalized_username:
        raise HTTPException(status_code=400, detail="Kullanıcı adı gerekli")
    if normalized_email == "":
        normalized_email = None
    return (
        normalized_username,
        normalized_first,
        normalized_last,
        normalized_email,
    )


def _ensure_unique_user(
    db: Session,
    *,
    username: str,
    email: str | None,
    exclude_user_id: int | None = None,
) -> None:
    username_query = db.query(User).filter(User.username == username)
    if exclude_user_id is not None:
        username_query = username_query.filter(User.id != exclude_user_id)
    existing_username = username_query.first()
    if existing_username:
        raise HTTPException(
            status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor"
        )

    if email:
        email_query = db.query(User).filter(User.email == email)
        if exclude_user_id is not None:
            email_query = email_query.filter(User.id != exclude_user_id)
        existing_email = email_query.first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Bu e-posta zaten kayıtlı")


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
    (
        normalized_username,
        normalized_first,
        normalized_last,
        normalized_email,
    ) = _normalize_user_fields(username, first_name, last_name, email)

    _ensure_unique_user(db, username=normalized_username, email=normalized_email)

    u = User(
        username=normalized_username,
        password_hash=hash_password(password),
        first_name=normalized_first,
        last_name=normalized_last,
        full_name=f"{normalized_first} {normalized_last}".strip(),
        email=normalized_email,
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
    normalized_type = donanim_tipi.strip()
    if not normalized_type:
        raise HTTPException(status_code=400, detail="Donanım tipi gerekli")

    product_table = models.Product.__table__
    bind = db.get_bind()
    if bind is None:
        bind = db.connection()
    product_table.create(bind=bind, checkfirst=True)

    item = models.Product(
        donanim_tipi=normalized_type,
        marka=marka or None,
        model=model or None,
        kullanim_alani=kullanim_alani or None,
        lisans_adi=lisans_adi or None,
        fabrika=fabrika or None,
    )
    db.add(item)
    db.commit()
    return RedirectResponse(url="/admin#products", status_code=303)


def _user_edit_post(
    uid: int,
    request: Request | None = None,
    username: str = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    is_admin: bool = Form(False),
    user: SessionUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    (
        normalized_username,
        normalized_first,
        normalized_last,
        normalized_email,
    ) = _normalize_user_fields(username, first_name, last_name, email)

    u = db.get(User, uid)
    if not u:
        return _error_response(
            request,
            status_code=404,
            message="Kullanıcı bulunamadı.",
            title="İşlem gerçekleştirilemedi",
        )
    if u.role == "admin" and user.id != u.id and user.username.lower() != "admin":
        return _error_response(
            request,
            status_code=403,
            message="Adminler birbirini güncelleyemez.",
            title="Erişim reddedildi",
        )
    try:
        _ensure_unique_user(
            db,
            username=normalized_username,
            email=normalized_email,
            exclude_user_id=uid,
        )
    except HTTPException as exc:
        detail = (
            exc.detail if isinstance(exc.detail, str) else "Kullanıcı güncellenemedi."
        )
        return _error_response(
            request,
            status_code=exc.status_code or 400,
            message=detail,
            title="Geçersiz işlem",
        )
    u.username = normalized_username
    u.first_name = normalized_first
    u.last_name = normalized_last
    u.full_name = f"{normalized_first} {normalized_last}".strip()
    u.email = normalized_email
    u.role = "admin" if is_admin else "user"
    if password:
        u.password_hash = hash_password(password)
    db.add(u)
    db.commit()
    if request is not None:
        _set_flash(
            request,
            f'"{u.username}" kullanıcısı güncellendi.',
            title="Güncellendi",
            variant="success",
        )
    return RedirectResponse(url="/admin#users", status_code=303)


@router.post("/users/{uid}/edit")
def user_edit_post_endpoint(
    uid: int,
    request: Request,
    username: str = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    is_admin: bool = Form(False),
    user: SessionUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _user_edit_post(
        uid,
        request,
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        is_admin=is_admin,
        user=user,
        db=db,
    )


def _user_delete(
    uid: int,
    request: Request | None = None,
    user: SessionUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    target = db.get(User, uid)
    if not target:
        return _error_response(
            request,
            status_code=404,
            message="Kullanıcı bulunamadı.",
            title="İşlem gerçekleştirilemedi",
        )
    if target.username.lower() == "admin":
        return _error_response(
            request,
            status_code=403,
            message="Admin kullanıcısı silinemez.",
            title="Erişim reddedildi",
        )
    if user.username.lower() != "admin" and target.role == "admin":
        return _error_response(
            request,
            status_code=403,
            message="Adminler birbirini silemez.",
            title="Erişim reddedildi",
        )
    username = target.username
    db.delete(target)
    db.commit()
    if request is not None:
        _set_flash(
            request,
            f'"{username}" kullanıcısı silindi.',
            title="Silindi",
            variant="success",
        )
    return RedirectResponse(url="/admin#users", status_code=303)


@router.post("/users/{uid}/delete")
def user_delete_endpoint(
    uid: int,
    request: Request,
    user: SessionUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _user_delete(uid, request, user=user, db=db)


@router.get("/connections/ldap", response_class=HTMLResponse)
def ldap_get(request: Request, db: Session = Depends(get_db)):
    def g(k):
        s = db.query(Setting).filter_by(key=k).first()
        return s.value if s else ""

    ctx = {
        "request": request,
        "host": g("ldap.host"),
        "base_dn": g("ldap.base_dn"),
        "bind_dn": g("ldap.bind_dn"),
        "bind_password": g("ldap.bind_password"),
        "use_ssl": g("ldap.use_ssl"),
    }
    return templates.TemplateResponse("admin_ldap.html", ctx)


@router.post("/connections/ldap")
def ldap_post(
    host: str = Form(""),
    base_dn: str = Form(""),
    bind_dn: str = Form(""),
    bind_password: str = Form(""),
    use_ssl: str = Form("0"),
    db: Session = Depends(get_db),
):
    for k, v in [
        ("ldap.host", host),
        ("ldap.base_dn", base_dn),
        ("ldap.bind_dn", bind_dn),
        ("ldap.bind_password", bind_password),
        ("ldap.use_ssl", use_ssl),
    ]:
        s = db.query(Setting).filter_by(key=k).first()
        if not s:
            s = Setting(key=k, value=v)
            db.add(s)
        else:
            s.value = v
    db.commit()
    return RedirectResponse(url="/admin/connections/ldap", status_code=303)


# Module-level aliases for compatibility with tests/importers
user_edit_post = _user_edit_post
user_delete = _user_delete
