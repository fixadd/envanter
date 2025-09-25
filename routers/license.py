from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, text
from sqlalchemy.orm import Session
from starlette import status

from database import get_db
from models import Inventory, License, LicenseLog, LicenseName, StockTotal
from security import current_user
from utils.faults import FAULT_STATUS_SCRAP, resolve_fault
from utils.http import get_request_user_name
from utils.stock_log import create_stock_log

router = APIRouter(prefix="/lisans", tags=["Lisans"])
templates = Jinja2Templates(directory="templates")


@router.get("/export")
async def export_licenses(db: Session = Depends(get_db)):
    """Export all license records as an Excel file."""
    from io import BytesIO

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    headers = [
        "ID",
        "Lisans Adı",
        "Lisans Anahtarı",
        "Sorumlu Personel",
        "Bağlı Envanter No",
        "IFS No",
        "Mail Adresi",
        "Tarih",
        "İşlem Yapan",
        "Durum",
        "Notlar",
    ]
    ws.append(headers)

    rows = db.query(License).order_by(License.id.asc()).all()
    for r in rows:
        ws.append(
            [
                r.id,
                r.lisans_adi,
                r.lisans_anahtari,
                r.sorumlu_personel,
                r.bagli_envanter_no,
                r.ifs_no,
                r.mail_adresi,
                r.tarih,
                r.islem_yapan,
                r.durum,
                r.notlar,
            ]
        )

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    headers = {"Content-Disposition": "attachment; filename=licenses.xlsx"}
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/import", response_class=PlainTextResponse)
async def import_licenses(file: UploadFile = File(...)):
    return f"Received {file.filename}, but import is not implemented."


def _logla(db: Session, lic: License, islem: str, detay: str, islem_yapan: str):
    db.add(
        LicenseLog(license_id=lic.id, islem=islem, detay=detay, islem_yapan=islem_yapan)
    )
@router.get("/new", response_class=HTMLResponse, name="license.new")
def new_license_form(request: Request, db: Session = Depends(get_db)):
    envanterler = db.query(Inventory).order_by(Inventory.no).all()
    users = [
        r[0]
        for r in db.execute(
            text("SELECT full_name FROM users ORDER BY full_name")
        ).fetchall()
    ]
    license_names = db.query(LicenseName).order_by(LicenseName.name).all()
    return templates.TemplateResponse(
        "license_form.html",
        {
            "request": request,
            "license": None,
            "envanterler": envanterler,
            "users": users,
            "license_names": license_names,
            "form_action": "/lisans/new",
        },
    )


@router.post("/new", name="license.new_post")
def new_license_post(
    request: Request,
    adi: str = Form(...),
    anahtar: str = Form(""),
    sorumlu_personel: str = Form(""),
    inventory_id: int = Form(None),
    ifs_no: str = Form(""),
    mail_adresi: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    inv = db.get(Inventory, inventory_id) if inventory_id else None
    lic = License(
        lisans_adi=adi,
        lisans_anahtari=anahtar or None,
        sorumlu_personel=sorumlu_personel or None,
        inventory_id=inv.id if inv else None,
        bagli_envanter_no=getattr(inv, "no", None),
        ifs_no=ifs_no or None,
        mail_adresi=mail_adresi or None,
        tarih=datetime.utcnow(),
        islem_yapan=getattr(user, "full_name", None) or "system",
    )
    db.add(lic)
    db.commit()
    _logla(
        db,
        lic,
        "EKLE",
        "Lisans oluşturuldu",
        getattr(user, "full_name", None) or "system",
    )
    db.commit()
    return RedirectResponse(
        url=request.url_for("license_list"), status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/create")
def create_license(
    request: Request,
    lisans_adi: str = Form(...),
    lisans_anahtari: str = Form(...),
    sorumlu_personel: str = Form(...),
    bagli_envanter_no: str = Form(...),
    mail_adresi: str | None = Form(None),
    ifs_no: str = Form(None),
    db: Session = Depends(get_db),
):
    lic = License(
        lisans_adi=lisans_adi,
        lisans_anahtari=lisans_anahtari,
        sorumlu_personel=sorumlu_personel,
        bagli_envanter_no=bagli_envanter_no,
        mail_adresi=mail_adresi,
        ifs_no=ifs_no,
        tarih=datetime.utcnow(),
        islem_yapan=get_request_user_name(request),
    )
    db.add(lic)
    db.commit()
    return RedirectResponse(url="/lisans", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{lic_id}/edit", response_class=HTMLResponse, name="license.edit_form")
def edit_license_form(
    lic_id: int, request: Request, modal: bool = False, db: Session = Depends(get_db)
):
    lic = db.get(License, lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    envanterler = db.query(Inventory).order_by(Inventory.no).all()
    users = [
        r[0]
        for r in db.execute(
            text("SELECT full_name FROM users ORDER BY full_name")
        ).fetchall()
    ]
    license_names = db.query(LicenseName).order_by(LicenseName.name).all()
    return templates.TemplateResponse(
        "license_form.html",
        {
            "request": request,
            "license": lic,
            "envanterler": envanterler,
            "users": users,
            "license_names": license_names,
            "form_action": f"/lisans/{lic_id}/edit",
            "modal": modal,
        },
    )


@router.post("/{lic_id}/edit", name="license.edit_post")
def edit_license_post(
    lic_id: int,
    request: Request,
    adi: str = Form(...),
    anahtar: str = Form(""),
    sorumlu_personel: str = Form(""),
    inventory_id: int = Form(None),
    ifs_no: str = Form(""),
    mail_adresi: str = Form(""),
    modal: bool = False,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    lic = db.get(License, lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    inv = db.get(Inventory, inventory_id) if inventory_id else None
    lic.lisans_adi = adi
    lic.lisans_anahtari = anahtar or None
    lic.sorumlu_personel = sorumlu_personel or None
    lic.inventory_id = inv.id if inv else None
    lic.bagli_envanter_no = getattr(inv, "no", None)
    lic.ifs_no = ifs_no or None
    lic.mail_adresi = mail_adresi or None
    _logla(
        db,
        lic,
        "DUZENLE",
        "Lisans düzenlendi",
        getattr(user, "full_name", None) or "system",
    )
    db.commit()
    if modal:
        return HTMLResponse(
            "<script>window.parent.postMessage('modal-close','*');</script>"
        )
    return RedirectResponse(
        url=request.url_for("license_list"), status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/{lic_id}/assign", response_class=HTMLResponse, name="license.assign_form")
def assign_license_form(
    lic_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    lic = db.get(License, lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    envanterler = db.query(Inventory).order_by(Inventory.no).all()
    users = [
        r[0]
        for r in db.execute(
            text("SELECT full_name FROM users ORDER BY full_name")
        ).fetchall()
    ]
    return templates.TemplateResponse(
        "license_assign.html",
        {
            "request": request,
            "license": lic,
            "envanterler": envanterler,
            "users": users,
            "current_user": user,
        },
    )


@router.post("/{lic_id}/assign")
def assign_license(
    lic_id: int,
    sorumlu_personel: str = Form(...),
    bagli_envanter_no: str = Form(""),
    islem_yapan: str = Form("system"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    lic = db.get(License, lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    eski_sp = lic.sorumlu_personel or ""
    eski_bagli = lic.bagli_envanter_no or ""
    lic.sorumlu_personel = (sorumlu_personel or "").strip() or None
    lic.bagli_envanter_no = (bagli_envanter_no or "").strip() or None
    _logla(
        db,
        lic,
        "ATAMA",
        f"Sorumlu: '{eski_sp}' -> '{lic.sorumlu_personel}', Bağlı Envanter: '{eski_bagli}' -> '{lic.bagli_envanter_no}'",
        islem_yapan,
    )
    db.commit()
    return RedirectResponse(
        url=request.url_for("license_list"), status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/{lic_id}/stock")
def stock_license(
    lic_id: int, db: Session = Depends(get_db), user=Depends(current_user)
):
    lic = db.get(License, lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    actor = getattr(user, "full_name", None) or user.username

    # Stoka alınan lisansın mevcut bağlantısını temizle
    lic.sorumlu_personel = None
    lic.bagli_envanter_no = None
    lic.inventory_id = None

    create_stock_log(
        db,
        donanim_tipi=lic.lisans_adi,
        miktar=1,
        ifs_no=lic.ifs_no,
        lisans_anahtari=lic.lisans_anahtari,
        mail_adresi=lic.mail_adresi,
        islem="girdi",
        actor=actor,
        source_type="lisans",
        source_id=lic.id,
    )

    total = db.get(StockTotal, lic.lisans_adi) or StockTotal(
        donanim_tipi=lic.lisans_adi, toplam=0
    )
    total.toplam += 1
    db.merge(total)

    _logla(db, lic, "STOK", "Stok girişi yapıldı", actor)
    db.commit()
    return RedirectResponse(
        url="/stock?tab=status&module=license",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{lic_id}/scrap")
def scrap_license(
    lic_id: int,
    aciklama: str = Form(""),
    islem_yapan: str = Form("system"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    lic = db.get(License, lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    eski_sp = lic.sorumlu_personel
    eski_env = lic.bagli_envanter_no
    lic.sorumlu_personel = None
    lic.bagli_envanter_no = None
    lic.inventory_id = None
    lic.durum = "hurda"
    if aciklama:
        lic.notlar = (lic.notlar + "\n" if lic.notlar else "") + aciklama
    detay = "Lisans hurdaya ayrıldı."
    if eski_sp or eski_env:
        detay += f" Sorumlu: {eski_sp or '-'}; Bağlı Envanter: {eski_env or '-'}"
    if aciklama:
        detay += f" Not: {aciklama}"
    _logla(db, lic, "HURDA", detay, islem_yapan)
    create_stock_log(
        db,
        donanim_tipi=lic.lisans_adi,
        miktar=1,
        ifs_no=lic.ifs_no,
        lisans_anahtari=lic.lisans_anahtari,
        mail_adresi=lic.mail_adresi,
        islem="hurda",
        actor=islem_yapan,
    )
    resolve_fault(
        db,
        "license",
        entity_id=lic.id,
        status=FAULT_STATUS_SCRAP,
        actor=islem_yapan,
        note="Hurdaya ayrıldı",
    )
    db.commit()
    return RedirectResponse(
        url=request.url_for("license_scrap_list"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{lic_id}/editquick")
def edit_quick_license(
    lic_id: int,
    notlar: str = Form(""),
    islem_yapan: str = Form("system"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    lic = db.get(License, lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    eski = getattr(lic, "notlar", "")
    setattr(lic, "notlar", notlar)
    _logla(db, lic, "DUZENLE", f"Not: '{eski}' -> '{notlar}'", islem_yapan)
    db.commit()
    return RedirectResponse(
        url=request.url_for("license_list"), status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("", name="license_list")
def license_list(
    request: Request, db: Session = Depends(get_db), current_user=Depends(current_user)
):
    active_licenses = or_(License.durum.is_(None), License.durum != "hurda")
    items = db.query(License).filter(active_licenses).all()
    users = [
        r[0]
        for r in db.execute(
            text("SELECT full_name FROM users ORDER BY full_name")
        ).fetchall()
    ]
    envanterler = db.query(Inventory).order_by(Inventory.no).all()
    license_names = db.query(LicenseName).order_by(LicenseName.name).all()
    return templates.TemplateResponse(
        "license_list.html",
        {
            "request": request,
            "items": items,
            "users": users,
            "envanterler": envanterler,
            "license_names": license_names,
            "current_user": current_user,
        },
    )


@router.get("/hurdalar", name="license_scrap_list")
def license_scrap_list(request: Request, db: Session = Depends(get_db)):
    items = db.query(License).filter(License.durum == "hurda").all()
    return templates.TemplateResponse(
        "license_scrap_list.html", {"request": request, "items": items}
    )


@router.get(
    "/detail/{lic_id}", response_class=HTMLResponse, name="license.detail_partial"
)
def license_detail_partial(
    lic_id: int, request: Request, db: Session = Depends(get_db)
):
    lic = db.get(License, lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    return templates.TemplateResponse(
        "partials/license_detail.html", {"request": request, "item": lic}
    )


@router.get("/{lic_id}", name="license_detail")
def license_detail(lic_id: int, request: Request, db: Session = Depends(get_db)):
    lic = db.get(License, lic_id)
    if not lic:
        raise HTTPException(status_code=404, detail="Lisans bulunamadı")
    return templates.TemplateResponse(
        "license_detail.html", {"request": request, "item": lic}
    )
