from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from models import User, Lookup
from auth import get_db
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
def admin_index(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.full_name.asc()).all()

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
        "lookup_kullanim_alanlari": get("kullanim_alani"),
        "lookup_lisans_adlari": get("lisans_adi"),
        "lookup_fabrikalar": get("fabrika"),
        "lookup_donanim_tipleri": get("donanim_tipi"),
        "lookup_markalar": get("marka"),
        "lookup_modeller": get("model"),
    }
    return templates.TemplateResponse("admin.html", ctx)

@router.post("/users/create")
def create_user(
    full_name: str = Form(...),
    email: str = Form(...),
    role: str = Form("user"),
    db: Session = Depends(get_db),
):
    u = User(full_name=full_name, email=email, role=role)
    db.add(u)
    db.commit()
    return RedirectResponse(url="/admin#users", status_code=303)

@router.post("/products/create")
def create_product(
    donanim_tipi: str = Form(...),
    marka: str = Form(""),
    model: str = Form(""),
    seri_no: str = Form(""),
    kullanim_alani: str = Form(""),
    lisans_adi: str = Form(""),
    fabrika: str = Form(""),
    notlar: str = Form(""),
    db: Session = Depends(get_db),
):
    # TODO: Kendi Inventory/Product modeline göre kaydı yap
    # item = Inventory(...); db.add(item)
    db.commit()
    return RedirectResponse(url="/admin#products", status_code=303)
