from fastapi import APIRouter, Depends, Request, Form, HTTPException
from sqlalchemy.orm import Session
from starlette import status
from fastapi.responses import RedirectResponse
from database import get_db
from models import License, LicenseLog
from fastapi.templating import Jinja2Templates
from security import current_user

router = APIRouter(prefix="/lisans", tags=["Lisans"])
templates = Jinja2Templates(directory="templates")


def _logla(db: Session, lic: License, islem: str, detay: str, islem_yapan: str):
    db.add(LicenseLog(license_id=lic.id, islem=islem, detay=detay, islem_yapan=islem_yapan))


@router.post("/{lic_id}/assign")
def assign_license(
    lic_id: int,
    sorumlu_personel: str = Form(...),
    bagli_envanter_no: str = Form(""),
    islem_yapan: str = Form("system"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    lic = db.query(License).get(lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    eski_sp = lic.sorumlu_personel or ""
    eski_bagli = lic.bagli_envanter_no or ""
    lic.sorumlu_personel = (sorumlu_personel or "").strip() or None
    lic.bagli_envanter_no = (bagli_envanter_no or "").strip() or None
    _logla(db, lic, "ATAMA", f"Sorumlu: '{eski_sp}' -> '{lic.sorumlu_personel}', Bağlı Envanter: '{eski_bagli}' -> '{lic.bagli_envanter_no}'", islem_yapan)
    db.commit()
    return RedirectResponse(url=request.url_for("license_list"), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{lic_id}/scrap")
def scrap_license(
    lic_id: int,
    islem_yapan: str = Form("system"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    lic = db.query(License).get(lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    lic.durum = "hurda"
    _logla(db, lic, "HURDA", "Lisans hurdaya ayrıldı.", islem_yapan)
    db.commit()
    return RedirectResponse(url=request.url_for("license_scrap_list"), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{lic_id}/editquick")
def edit_quick_license(
    lic_id: int,
    notlar: str = Form(""),
    islem_yapan: str = Form("system"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    lic = db.query(License).get(lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    eski = getattr(lic, "notlar", "")
    setattr(lic, "notlar", notlar)
    _logla(db, lic, "DUZENLE", f"Not: '{eski}' -> '{notlar}'", islem_yapan)
    db.commit()
    return RedirectResponse(url=request.url_for("license_list"), status_code=status.HTTP_303_SEE_OTHER)


@router.get("", name="license_list")
def license_list(request: Request, db: Session = Depends(get_db), current_user=Depends(current_user)):
    items = db.query(License).filter(License.durum != "hurda").all()
    users = []
    envanterler = []
    return templates.TemplateResponse("license_list.html", {"request": request, "items": items, "users": users, "envanterler": envanterler, "current_user": current_user})


@router.get("/hurdalar", name="license_scrap_list")
def license_scrap_list(request: Request, db: Session = Depends(get_db)):
    items = db.query(License).filter(License.durum == "hurda").all()
    return templates.TemplateResponse("license_scrap_list.html", {"request": request, "items": items})


@router.get("/{lic_id}", name="license_detail")
def license_detail(lic_id: int, request: Request, db: Session = Depends(get_db)):
    lic = db.query(License).get(lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    return templates.TemplateResponse("license_detail.html", {"request": request, "item": lic})
