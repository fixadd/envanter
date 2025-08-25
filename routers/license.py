from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from models import License, Inventory, LicenseLog
from database import get_db


router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ———— Liste ——————————————————————————————
@router.get("/licenses", name="license_list")
def license_list(request: Request, db: Session = Depends(get_db)):
    lisanslar = (
        db.query(License)
        .options(joinedload(License.inventory))
        .order_by(License.id.desc())
        .all()
    )
    return templates.TemplateResponse(
        "license_list.html", {"request": request, "lisanslar": lisanslar}
    )


# ———— Yeni ——————————————————————————————
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
    anahtar: Optional[str] = Form(None),
    sorumlu_personel: Optional[str] = Form(None),
    inventory_id: Optional[int] = Form(None),
    ifs_no: Optional[str] = Form(None),
    tarih: Optional[str] = Form(None),
    islem_yapan: Optional[str] = Form(None),
    mail_adresi: Optional[str] = Form(None),
):
    lic = License(
        adi=adi,
        anahtar=anahtar,
        sorumlu_personel=sorumlu_personel,
        inventory_id=inventory_id or None,
        ifs_no=ifs_no,
        tarih=date.fromisoformat(tarih) if tarih else None,
        islem_yapan=islem_yapan,
        mail_adresi=mail_adresi,
    )
    db.add(lic)
    db.commit()
    return RedirectResponse(request.url_for("license_list"), status_code=303)


# ———— Düzenle —————————————————————————————
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
    anahtar: Optional[str] = Form(None),
    sorumlu_personel: Optional[str] = Form(None),
    inventory_id: Optional[int] = Form(None),
    ifs_no: Optional[str] = Form(None),
    tarih: Optional[str] = Form(None),
    islem_yapan: Optional[str] = Form(None),
    mail_adresi: Optional[str] = Form(None),
):
    lic = db.get(License, id)
    logs: list[LicenseLog] = []

    def add_log(field: str, old, new):
        logs.append(
            LicenseLog(
                license_id=lic.id,
                field=field,
                old_value=str(old) if old is not None else None,
                new_value=str(new) if new is not None else None,
                changed_by=islem_yapan or "Sistem",
                changed_at=datetime.utcnow(),
            )
        )

    if lic.sorumlu_personel != sorumlu_personel:
        add_log("sorumlu_personel", lic.sorumlu_personel, sorumlu_personel)

    if (lic.inventory_id or None) != (inventory_id or None):
        old_no = None
        new_no = None
        if lic.inventory_id:
            inv_old = db.get(Inventory, lic.inventory_id)
            old_no = inv_old.no if inv_old else None
        if inventory_id:
            inv_new = db.get(Inventory, inventory_id)
            new_no = inv_new.no if inv_new else None
        add_log("bagli_envanter_no", old_no, new_no)

    lic.adi = adi
    lic.anahtar = anahtar
    lic.sorumlu_personel = sorumlu_personel
    lic.inventory_id = inventory_id or None
    lic.ifs_no = ifs_no
    lic.tarih = date.fromisoformat(tarih) if tarih else None
    lic.islem_yapan = islem_yapan
    lic.mail_adresi = mail_adresi

    for lg in logs:
        db.add(lg)

    db.commit()
    return RedirectResponse(request.url_for("license_list"), status_code=303)


# ———— Detay —————————————————————————————
@router.get("/licenses/{id}", name="license_detail")
def license_detail(id: int, request: Request, db: Session = Depends(get_db)):
    lic = (
        db.query(License)
        .options(joinedload(License.inventory))
        .filter(License.id == id)
        .first()
    )
    logs = (
        db.query(LicenseLog)
        .filter(LicenseLog.license_id == id)
        .order_by(LicenseLog.changed_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "license_detail.html",
        {"request": request, "license": lic, "logs": logs},
    )

