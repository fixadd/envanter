from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse

from models import License, Inventory
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/licenses", name="license_list", response_class=HTMLResponse)
def license_list(request: Request, db: Session = Depends(get_db)):
    lisanslar = db.query(License).order_by(License.adi.asc()).all()
    return templates.TemplateResponse(
        "license_list.html", {"request": request, "lisanslar": lisanslar}
    )


@router.get("/licenses/new", name="license_new")
def license_new(request: Request, db: Session = Depends(get_db)):
    envanterler = db.query(Inventory).order_by(Inventory.no.asc()).all()
    return templates.TemplateResponse(
        "license_form.html",
        {
            "request": request,
            "form_action": request.url_for("license_create"),
            "license": None,
            "envanterler": envanterler,
        },
    )


@router.post("/licenses", name="license_create")
def license_create(
    request: Request,
    db: Session = Depends(get_db),
    adi: str = Form(...),
    vendor: str | None = Form(None),
    anahtar: str | None = Form(None),
    son_kullanma: str | None = Form(None),
    inventory_id: int | None = Form(None),
):
    lic = License(
        adi=adi,
        vendor=vendor,
        anahtar=anahtar,
        son_kullanma=son_kullanma or None,
        inventory_id=inventory_id or None,
    )
    db.add(lic)
    db.commit()
    return RedirectResponse(request.url_for("license_list"), status_code=303)


@router.get("/licenses/{id}/edit", name="license_edit")
def license_edit(id: int, request: Request, db: Session = Depends(get_db)):
    lic = db.get(License, id)
    envanterler = db.query(Inventory).order_by(Inventory.no.asc()).all()
    return templates.TemplateResponse(
        "license_form.html",
        {
            "request": request,
            "form_action": request.url_for("license_update", id=id),
            "license": lic,
            "envanterler": envanterler,
        },
    )


@router.post("/licenses/{id}", name="license_update")
def license_update(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    adi: str = Form(...),
    vendor: str | None = Form(None),
    anahtar: str | None = Form(None),
    son_kullanma: str | None = Form(None),
    inventory_id: int | None = Form(None),
):
    lic = db.get(License, id)
    lic.adi = adi
    lic.vendor = vendor
    lic.anahtar = anahtar
    lic.son_kullanma = son_kullanma or None
    lic.inventory_id = inventory_id or None
    db.commit()
    return RedirectResponse(request.url_for("license_list"), status_code=303)


@router.get("/licenses/{id}", name="license_detail", response_class=HTMLResponse)
def license_detail(id: int, request: Request, db: Session = Depends(get_db)):
    lic = db.get(License, id)
    return templates.TemplateResponse(
        "license_detail.html", {"request": request, "license": lic}
    )
