from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
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
    ifs_no: List[str] = Form([]),
    miktar: List[int] = Form([]),
    marka: List[str] = Form([]),
    model: List[str] = Form([]),
    envanter_no: Optional[str] = Form(None),
    sorumlu_personel: Optional[str] = Form(None),
    bagli_envanter_no: Optional[str] = Form(None),
    lisans_adi: Optional[str] = Form(None),
    aciklama: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    created_ids: List[int] = []
    if tur == TalepTuru.AKSESUAR and ifs_no:
        for idx, no in enumerate(ifs_no):
            talep = Talep(
                tur=tur,
                donanim_tipi=donanim_tipi,
                ifs_no=no or None,
                miktar=miktar[idx] if idx < len(miktar) else None,
                marka=marka[idx] if idx < len(marka) else None,
                model=model[idx] if idx < len(model) else None,
                aciklama=aciklama,
            )
            db.add(talep)
            db.flush()
            created_ids.append(talep.id)
    else:
        talep = Talep(
            tur=tur,
            donanim_tipi=donanim_tipi,
            ifs_no=ifs_no[0] if ifs_no else None,
            miktar=miktar[0] if miktar else None,
            marka=marka[0] if marka else None,
            model=model[0] if model else None,
            envanter_no=envanter_no,
            sorumlu_personel=sorumlu_personel,
            bagli_envanter_no=bagli_envanter_no,
            lisans_adi=lisans_adi,
            aciklama=aciklama,
        )
        db.add(talep)
        db.flush()
        created_ids.append(talep.id)

    db.commit()
    return {"ok": True, "ids": created_ids}


@router.post("/{talep_id}/cancel", response_class=JSONResponse)
def cancel_request(talep_id: int, db: Session = Depends(get_db)):
    talep = db.get(Talep, talep_id)
    if not talep:
        return JSONResponse({"ok": False}, status_code=404)
    talep.durum = TalepDurum.IPTAL
    db.commit()
    return {"ok": True}


@router.post("/{talep_id}/close", response_class=JSONResponse)
def close_request(talep_id: int, db: Session = Depends(get_db)):
    talep = db.get(Talep, talep_id)
    if not talep:
        return JSONResponse({"ok": False}, status_code=404)
    talep.durum = TalepDurum.TAMAMLANDI
    db.commit()
    return {"ok": True}


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
