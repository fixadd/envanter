from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from io import BytesIO
from openpyxl import Workbook
from datetime import datetime

from models import Talep, TalepTuru, TalepDurum, HardwareType, Brand, Model
from database import get_db
from fastapi.templating import Jinja2Templates
from sqlalchemy import cast, Integer

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/talepler", tags=["Talepler"])


@router.get("", response_class=HTMLResponse, name="talep_list")
def liste(request: Request, durum: str = "acik", db: Session = Depends(get_db)):
    """Talep kayıtlarını duruma göre tablo halinde göster."""

    durum_map = {
        "acik": TalepDurum.ACIK,
        "tamamlandi": TalepDurum.TAMAMLANDI,
        "iptal": TalepDurum.IPTAL,
    }
    selected = durum_map.get(durum, TalepDurum.ACIK)
    q = (
        db.query(
            Talep,
            HardwareType.name.label("dt_name"),
            Brand.name.label("marka_name"),
            Model.name.label("model_name"),
        )
        .outerjoin(HardwareType, HardwareType.id == cast(Talep.donanim_tipi, Integer))
        .outerjoin(Brand, Brand.id == cast(Talep.marka, Integer))
        .outerjoin(Model, Model.id == cast(Talep.model, Integer))
        .filter(Talep.durum == selected)
        .order_by(Talep.ifs_no.asc(), Talep.id.asc())
    )

    rows = []
    for t, dt_name, marka_name, model_name in q.all():
        t.donanim_tipi = dt_name or t.donanim_tipi
        t.marka = marka_name or t.marka
        t.model = model_name or t.model
        rows.append(t)

    return templates.TemplateResponse(
        "talepler.html",
        {
            "request": request,
            "rows": rows,
            "durum": durum,
        },
    )


@router.post("", response_class=JSONResponse)
def olustur(
    donanim_tipi: Optional[str] = Form(None),
    ifs_no: Optional[str] = Form(None),
    miktar: Optional[int] = Form(None),
    marka: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    aciklama: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    talep = Talep(
        tur=TalepTuru.AKSESUAR,
        donanim_tipi=donanim_tipi,
        ifs_no=ifs_no,
        miktar=miktar or 1,
        karsilanan_miktar=0,
        kalan_miktar=miktar or 1,
        marka=marka,
        model=model,
        aciklama=aciklama,
    )
    db.add(talep)
    db.commit()
    db.refresh(talep)
    return {"ok": True, "ids": [talep.id]}


@router.post("/{talep_id}/cancel", response_class=JSONResponse)
def cancel_request(talep_id: int, adet: int = Form(1), db: Session = Depends(get_db)):
    if adet <= 0:
        return JSONResponse({"ok": False, "error": "Adet 0'dan büyük olmalı"}, status_code=400)
    talep = db.get(Talep, talep_id)
    if not talep:
        return JSONResponse({"ok": False}, status_code=404)
    if talep.durum != TalepDurum.ACIK:
        return JSONResponse({"ok": False, "error": "Talep kapalı"}, status_code=400)
    kalan = talep.kalan_miktar
    if kalan > adet:
        talep.miktar -= adet
        talep.kalan_miktar = kalan - adet
        talep.durum = TalepDurum.ACIK
    else:
        talep.miktar -= kalan
        talep.kalan_miktar = 0
        talep.durum = TalepDurum.IPTAL
        talep.kapanma_tarihi = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/{talep_id}/close", response_class=JSONResponse)
def close_request(talep_id: int, adet: int = Form(1), db: Session = Depends(get_db)):
    if adet <= 0:
        return JSONResponse({"ok": False, "error": "Adet 0'dan büyük olmalı"}, status_code=400)
    talep = db.get(Talep, talep_id)
    if not talep:
        return JSONResponse({"ok": False}, status_code=404)
    if talep.durum != TalepDurum.ACIK:
        return JSONResponse({"ok": False, "error": "Talep kapalı"}, status_code=400)
    kalan = talep.kalan_miktar
    if kalan > adet:
        talep.karsilanan_miktar += adet
        talep.kalan_miktar = kalan - adet
        talep.durum = TalepDurum.ACIK
    else:
        talep.karsilanan_miktar += kalan
        talep.kalan_miktar = 0
        talep.durum = TalepDurum.TAMAMLANDI
        talep.kapanma_tarihi = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/{talep_id}/stock", response_class=JSONResponse)
def convert_request_to_stock(
    talep_id: int,
    adet: int = Form(1),
    islem_yapan: str = Form("Sistem"),
    marka: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    ifs_no: Optional[str] = Form(None),
    aciklama: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Convert an active request into a stock entry.

    Creates a ``StockLog`` record using the information stored on the
    ``Talep`` and decreases the remaining quantity on the request.  When the
    request is fully processed its status is marked as closed.
    """

    if adet <= 0:
        return JSONResponse(
            {"ok": False, "error": "Adet 0'dan büyük olmalı"}, status_code=400
        )

    talep = db.get(Talep, talep_id)
    if not talep:
        return JSONResponse({"ok": False}, status_code=404)

    kalan = talep.kalan_miktar
    if kalan < adet:
        return JSONResponse(
            {"ok": False, "error": "Yetersiz talep miktarı"}, status_code=400
        )

    from routers.stock import stock_add

    def _val(x):
        return getattr(x, "default", x)

    marka = _val(marka) or talep.marka
    model = _val(model) or talep.model
    ifs_no = _val(ifs_no) or talep.ifs_no
    aciklama = _val(aciklama)
    islem_yapan = _val(islem_yapan) or "Sistem"
    if not marka or not model:
        return JSONResponse(
            {"ok": False, "error": "Marka ve model gerekli"}, status_code=400
        )

    # persist provided details back to request
    talep.marka = marka
    talep.model = model
    talep.ifs_no = ifs_no
    if aciklama:
        talep.aciklama = aciklama

    payload = {
        "is_lisans": talep.tur == TalepTuru.LISANS,
        "donanim_tipi": talep.donanim_tipi,
        "miktar": adet,
        "marka": marka,
        "model": model,
        "ifs_no": ifs_no,
        "aciklama": aciklama,
        "islem_yapan": islem_yapan,
        "source_type": "talep",
        "source_id": talep.id,
    }

    result = stock_add(payload, db)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)

    talep.karsilanan_miktar += adet
    talep.kalan_miktar = kalan - adet
    if talep.kalan_miktar > 0:
        talep.durum = TalepDurum.ACIK
    else:
        talep.durum = TalepDurum.TAMAMLANDI
        talep.kapanma_tarihi = datetime.utcnow()

    db.commit()
    return {"ok": True, "stock_id": result.get("id")}


@router.get("/convert/{talep_id}", response_class=HTMLResponse)
def convert_request(talep_id: int, request: Request, adet: int = 1, db: Session = Depends(get_db)):
    if adet <= 0:
        return HTMLResponse(status_code=400)
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


@router.get("/export.xlsx", name="talep_export_excel")
def export_excel(db: Session = Depends(get_db)):
    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "ID",
            "Tür",
            "Donanım Tipi",
            "IFS No",
            "İstenen",
            "Karşılanan",
            "Kalan",
            "Marka",
            "Model",
            "Envanter No",
            "Lisans Adı",
            "Sorumlu",
            "Açıklama",
            "Durum",
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
                t.karsilanan_miktar,
                t.kalan_miktar,
                t.marka,
                t.model,
                t.envanter_no or t.bagli_envanter_no,
                t.lisans_adi,
                t.sorumlu_personel,
                t.aciklama,
                t.durum.value,
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
