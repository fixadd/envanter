from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from io import BytesIO
from openpyxl import Workbook

from models import Talep, TalepTuru, TalepDurum
from database import get_db
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/talepler", tags=["Talepler"])


@router.get("", response_class=HTMLResponse)
def liste(request: Request, db: Session = Depends(get_db)):
    """Talep kayıtlarını duruma göre tablo halinde göster."""

    aktif = db.query(Talep).filter(Talep.durum == TalepDurum.AKTIF).all()
    kapali = db.query(Talep).filter(Talep.durum == TalepDurum.TAMAMLANDI).all()
    iptal = db.query(Talep).filter(Talep.durum == TalepDurum.IPTAL).all()

    return templates.TemplateResponse(
        "talepler.html",
        {
            "request": request,
            "aktif": aktif,
            "kapali": kapali,
            "iptal": iptal,
        },
    )


@router.post("", response_class=JSONResponse)
def olustur(
    tur: TalepTuru = Form(...),
    donanim_tipi: Optional[str] = Form(None),
    ifs_no: Optional[str] = Form(None),
    miktar: Optional[int] = Form(None),
    marka: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    envanter_no: Optional[str] = Form(None),
    sorumlu_personel: Optional[str] = Form(None),
    bagli_envanter_no: Optional[str] = Form(None),
    lisans_adi: Optional[str] = Form(None),
    aciklama: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    talep = Talep(
        tur=tur,
        donanim_tipi=donanim_tipi,
        ifs_no=ifs_no,
        miktar=miktar,
        marka=marka,
        model=model,
        envanter_no=envanter_no,
        sorumlu_personel=sorumlu_personel,
        bagli_envanter_no=bagli_envanter_no,
        lisans_adi=lisans_adi,
        aciklama=aciklama,
    )
    db.add(talep)
    db.commit()
    db.refresh(talep)
    return {"ok": True, "ids": [talep.id]}


@router.post("/{talep_id}/cancel", response_class=JSONResponse)
def cancel_request(talep_id: int, adet: int = Form(1), db: Session = Depends(get_db)):
    talep = db.get(Talep, talep_id)
    if not talep:
        return JSONResponse({"ok": False}, status_code=404)
    mevcut = talep.miktar or 1
    if mevcut > adet:
        talep.miktar = mevcut - adet
    else:
        talep.durum = TalepDurum.IPTAL
        talep.miktar = 0
    db.commit()
    return {"ok": True}


@router.post("/{talep_id}/close", response_class=JSONResponse)
def close_request(talep_id: int, adet: int = Form(1), db: Session = Depends(get_db)):
    talep = db.get(Talep, talep_id)
    if not talep:
        return JSONResponse({"ok": False}, status_code=404)
    mevcut = talep.miktar or 1
    if mevcut > adet:
        talep.miktar = mevcut - adet
    else:
        talep.durum = TalepDurum.TAMAMLANDI
        talep.miktar = 0
    db.commit()
    return {"ok": True}


@router.get("/convert/{talep_id}", response_class=HTMLResponse)
def convert_request(talep_id: int, request: Request, adet: int = 1, db: Session = Depends(get_db)):
    talep = db.get(Talep, talep_id)
    if not talep:
        return HTMLResponse(status_code=404)
    fields = [
        f
        for f in [
            "envanter_no",
            "sorumlu_personel",
            "bagli_envanter_no",
            "lisans_adi",
            "donanim_tipi",
            "marka",
            "model",
        ]
        if not getattr(talep, f)
    ]
    return templates.TemplateResponse(
        "requests/convert.html",
        {"request": request, "talep": talep, "adet": adet, "eksik": fields},
    )


@router.get("/export.xlsx")
def export_excel(db: Session = Depends(get_db)):
    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "ID",
            "Tür",
            "Donanım Tipi",
            "IFS No",
            "Miktar",
            "Marka",
            "Model",
            "Envanter No",
            "Lisans Adı",
            "Sorumlu",
            "Açıklama",
            "Tarih",
        ]
    )
    rows = db.query(Talep).order_by(Talep.id.asc()).all()
    for t in rows:
        ws.append(
            [
                t.id,
                str(t.tur),
                t.donanim_tipi,
                t.ifs_no,
                t.miktar,
                t.marka,
                t.model,
                t.envanter_no or t.bagli_envanter_no,
                t.lisans_adi,
                t.sorumlu_personel,
                t.aciklama,
                t.olusturma_tarihi.strftime("%Y-%m-%d %H:%M"),
            ]
        )

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    headers = {"Content-Disposition": "attachment; filename=talepler.xlsx"}
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
