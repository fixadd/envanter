from __future__ import annotations

from datetime import datetime, date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette import status

from database import get_db
from models import Department, Factory, Inventory, License, User
from security import current_user

router = APIRouter(prefix="/licenses", tags=["Licenses"])
templates = Jinja2Templates(directory="templates")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Tarih formatı geçersiz") from exc


def _to_optional_int(value: str | None) -> int | None:
    if value in (None, "", "None"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Geçersiz sayısal değer") from exc


def _lists(db: Session) -> dict[str, object]:
    factories = db.query(Factory).order_by(Factory.name.asc()).all()
    departments = db.query(Department).order_by(Department.name.asc()).all()
    persons = (
        db.query(User)
        .order_by(User.full_name.asc(), User.username.asc())
        .all()
    )
    inventories = db.query(Inventory).order_by(Inventory.no.asc()).all()
    return {
        "factories": factories,
        "departments": departments,
        "persons": persons,
        "inventories": inventories,
    }


@router.get("", name="licenses.list")
def license_index(
    request: Request, db: Session = Depends(get_db), user=Depends(current_user)
):
    licenses = db.query(License).order_by(License.id.desc()).all()
    context = {"request": request, "licenses": licenses}
    context.update(_lists(db))
    return templates.TemplateResponse("licenses/list.html", context)


@router.post("/add", name="licenses.add")
def license_add(
    request: Request,
    license_code: str = Form(...),
    product_name: str = Form(...),
    factory_id: str | None = Form(None),
    department_id: str | None = Form(None),
    owner_id: str | None = Form(None),
    inventory_id: str | None = Form(None),
    license_type: str = Form(...),
    seat_count: int = Form(...),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
    license_key: str | None = Form(None),
    note: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    normalized_code = license_code.strip()
    if not normalized_code:
        raise HTTPException(status_code=400, detail="Lisans numarası gerekli")

    existing = (
        db.query(License)
        .filter(License.license_code == normalized_code)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Bu lisans numarası zaten kayıtlı")

    product = product_name.strip()
    if not product:
        raise HTTPException(status_code=400, detail="Ürün adı gerekli")

    seat = int(seat_count) if isinstance(seat_count, str) else seat_count
    if seat <= 0:
        raise HTTPException(
            status_code=400, detail="Koltuk sayısı 1 veya daha büyük olmalı"
        )

    start = _parse_date(start_date)
    end = _parse_date(end_date)

    factory_fk = _to_optional_int(factory_id)
    department_fk = _to_optional_int(department_id)
    owner_fk = _to_optional_int(owner_id)
    inventory_fk = _to_optional_int(inventory_id)

    owner = db.get(User, owner_fk) if owner_fk else None
    inventory = db.get(Inventory, inventory_fk) if inventory_fk else None

    lic = License(
        license_code=normalized_code,
        product_name=product,
        license_type=license_type,
        seat_count=seat,
        start_date=start,
        end_date=end,
        license_key=(license_key or "").strip() or None,
        note=(note or "").strip() or None,
        factory_id=factory_fk,
        department_id=department_fk,
        owner_id=owner_fk,
        inventory_id=inventory_fk,
    )

    if owner:
        lic.sorumlu_personel = owner.full_name or owner.username
    if inventory:
        lic.bagli_envanter_no = inventory.no

    lic.islem_yapan = (
        getattr(user, "full_name", None)
        or getattr(user, "username", "")
        or "system"
    )
    db.add(lic)
    db.commit()

    return RedirectResponse(url="/licenses", status_code=status.HTTP_303_SEE_OTHER)
