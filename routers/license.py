from fastapi import APIRouter, Depends, Request, HTTPException, Form
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse, RedirectResponse
from datetime import datetime
from models import License, LicenseLog, User, Inventory
from .license_schemas import LicenseCreate, LicenseUpdate
from auth import get_db

# from auth import require_login  # login varsa Depends(require_login) ile sarabilirsin

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/licenses", tags=["Lisanslar"])


@router.get("", response_class=HTMLResponse)
def license_list(request: Request, db: Session = Depends(get_db)):
    rows = (
        db.query(
            License.id,
            License.bagli_envanter_no,
            License.lisans_adi,
            License.lisans_anahtari,
            License.sorumlu_personel,
        )
        .order_by(License.id.desc())
        .all()
    )
    users = db.query(User).order_by(User.full_name).all()
    inventory_nos = [r.no for r in db.query(Inventory.no).order_by(Inventory.no).all()]
    return templates.TemplateResponse(
        "license_list.html",
        {"request": request, "rows": rows, "users": users, "inventory_nos": inventory_nos},
    )


@router.post("/add", response_class=HTMLResponse)
def license_add(
    request: Request,
    lisans_adi: str = Form(...),
    lisans_anahtari: str = Form(...),
    sorumlu_personel: str | None = Form(None),
    bagli_envanter_no: str | None = Form(None),
    ifs_no: str | None = Form(None),
    mail_adresi: str | None = Form(None),
    db: Session = Depends(get_db),
):
    payload = LicenseCreate(
        lisans_adi=lisans_adi,
        lisans_anahtari=lisans_anahtari,
        sorumlu_personel=sorumlu_personel,
        bagli_envanter_no=bagli_envanter_no,
        ifs_no=ifs_no,
        mail_adresi=mail_adresi,
        tarih=datetime.now().strftime("%Y-%m-%d"),
        islem_yapan=request.session.get("user_name"),
    )
    lic = License(**payload.model_dump())
    db.add(lic)
    db.commit()
    return RedirectResponse("/licenses", status_code=303)


@router.get("/{license_id}")
def license_detail(license_id: int, request: Request, db: Session = Depends(get_db)):
    lic = db.query(License).filter(License.id == license_id).first()
    if not lic:
        raise HTTPException(404, "Lisans bulunamadı")

    logs = (
        db.query(LicenseLog)
        .filter(LicenseLog.license_id == lic.id)
        .order_by(LicenseLog.changed_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "license_detail.html", {"request": request, "item": lic, "logs": logs}
    )


@router.post("")
def create_license(payload: LicenseCreate, db: Session = Depends(get_db)):
    lic = License(**payload.model_dump())
    db.add(lic)
    db.commit()
    return {"ok": True, "id": lic.id}


@router.post("/{license_id}/update")
def update_license(license_id: int, payload: LicenseUpdate, db: Session = Depends(get_db)):
    lic = db.query(License).filter(License.id == license_id).first()
    if not lic:
        raise HTTPException(404, "Lisans yok")

    mutable_fields = [
        "lisans_adi",
        "lisans_anahtari",
        "sorumlu_personel",
        "bagli_envanter_no",
        "ifs_no",
        "tarih",
        "islem_yapan",
        "mail_adresi",
    ]

    changer = payload.islem_yapan or "Sistem"

    changed = False
    for f in mutable_fields:
        new_val = getattr(payload, f, None)
        if new_val is None:
            continue
        old_val = getattr(lic, f)
        if new_val != old_val:
            setattr(lic, f, new_val)
            db.add(
                LicenseLog(
                    license_id=lic.id,
                    field=f,
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val) if new_val is not None else None,
                    changed_by=changer,
                )
            )
            changed = True

    if changed:
        db.commit()
    return {"ok": True}
