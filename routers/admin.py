from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from models import User, Lookup, Inventory
from auth import get_db, hash_password

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def admin_index(request: Request, q: str = "", role: str = "", db: Session = Depends(get_db)):
    users_q = db.query(User)
    if q:
        users_q = users_q.filter(
            (User.full_name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%"))
        )
    if role:
        users_q = users_q.filter(User.role == role)

    users = users_q.order_by(User.full_name.asc()).all()

    lookup_donanim_tipleri = (
        db.query(Lookup)
        .filter(Lookup.category == "donanim_tipi")
        .all()
    )
    inventory_refs = (
        db.query(Inventory)
        .with_entities(Inventory.no, Inventory.marka, Inventory.model)
        .limit(200)
        .all()
    )

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "users": users,
            "lookup_donanim_tipleri": lookup_donanim_tipleri,
            "inventory_refs": inventory_refs,
        },
    )


@router.post("/users/create")
def create_user(
    full_name: str = Form(...),
    email: str = Form(...),
    role: str = Form("user"),
    db: Session = Depends(get_db),
):
    username = email
    user = User(
        username=username,
        password_hash=hash_password("1234"),
        full_name=full_name,
        email=email,
        role=role,
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/admin#users", status_code=303)


@router.post("/products/create")
def create_product(
    donanim_tipi: str = Form(...),
    marka: str = Form(""),
    model: str = Form(""),
    seri_no: str = Form(""),
    sorumlu_personel: str = Form(""),
    bagli_envanter_no: str = Form(""),
    notlar: str = Form(""),
    db: Session = Depends(get_db),
):
    # new_item = Inventory(
    #     no="",  # Envanter numarası gibi zorunlu alanlar için uyarlayın
    #     donanim_tipi=donanim_tipi,
    #     marka=marka,
    #     model=model,
    #     seri_no=seri_no,
    #     sorumlu_personel=sorumlu_personel,
    #     bagli_envanter_no=bagli_envanter_no,
    #     not_=notlar,
    # )
    # db.add(new_item)
    db.commit()
    return RedirectResponse(url="/admin#products", status_code=303)
