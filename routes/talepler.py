from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Literal
from io import BytesIO
from openpyxl import Workbook
from datetime import datetime

from models import Talep, TalepTuru, TalepDurum, HardwareType, Brand, Model
from database import get_db
from fastapi.templating import Jinja2Templates
from sqlalchemy import cast, Integer

from utils.http import get_or_404, validate_adet

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/talepler", tags=["Talepler"])


def process_talep(talep: Talep, adet: int, is_cancel: bool = False) -> Talep:
    """Apply shared quantity handling logic for request operations."""

    if talep.durum != TalepDurum.ACIK:
        raise HTTPException(status_code=400, detail="Talep kapalı")

    kalan = talep.kalan_miktar or 0
    if adet > kalan:
        raise HTTPException(status_code=400, detail="Yetersiz talep miktarı")

    if is_cancel:
        talep.miktar -= adet
    else:
        talep.karsilanan_miktar += adet

    talep.kalan_miktar = kalan - adet

    if talep.kalan_miktar == 0:
        talep.durum = TalepDurum.IPTAL if is_cancel else TalepDurum.TAMAMLANDI
        talep.kapanma_tarihi = datetime.utcnow()
    else:
        talep.durum = TalepDurum.ACIK

    return talep


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


@router.post("")
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


@router.post("/{talep_id}/cancel")
def cancel_request(talep_id: int, adet: int = Form(1), db: Session = Depends(get_db)):
    validate_adet(adet)
    talep = get_or_404(db, Talep, talep_id)
    process_talep(talep, adet, is_cancel=True)
    db.commit()
    return {"ok": True}


@router.post("/{talep_id}/close")
def close_request(talep_id: int, adet: int = Form(1), db: Session = Depends(get_db)):
    validate_adet(adet)
    talep = get_or_404(db, Talep, talep_id)
    process_talep(talep, adet, is_cancel=False)
    db.commit()
    return {"ok": True}


@router.post("/{talep_id}/stock")
def convert_request_to_stock(
    talep_id: int,
    adet: int = Form(1),
    islem_yapan: str = Form("Sistem"),
    marka: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    ifs_no: Optional[str] = Form(None),
    aciklama: Optional[str] = Form(None),
    tur: Literal["envanter", "lisans", "yazici"] = Form("envanter"),
    db: Session = Depends(get_db),
):
    """Convert an active request into a stock entry.

    Creates a ``StockLog`` record using the information stored on the
    ``Talep`` and decreases the remaining quantity on the request.  When the
    request is fully processed its status is marked as closed.
    """

    validate_adet(adet)

    talep = get_or_404(db, Talep, talep_id)

    if talep.durum != TalepDurum.ACIK:
        raise HTTPException(status_code=400, detail="Talep kapalı")

    kalan = talep.kalan_miktar or 0
    if kalan < adet:
        raise HTTPException(status_code=400, detail="Yetersiz talep miktarı")

    from routers.stock import stock_add

    def _val(x):
        return getattr(x, "default", x)

    selected_type = str(_val(tur) or "envanter").strip().lower()
    if selected_type not in {"envanter", "lisans", "yazici"}:
        selected_type = "envanter"

    marka = _val(marka) or talep.marka
    model = _val(model) or talep.model
    ifs_no = _val(ifs_no) or talep.ifs_no
    aciklama = _val(aciklama)
    islem_yapan = _val(islem_yapan) or "Sistem"
    if selected_type != "lisans" and (not marka or not model):
        raise HTTPException(status_code=400, detail="Marka ve model gerekli")

    if selected_type == "lisans":
        marka = marka or None
        model = model or None

    # persist provided details back to request
    talep.marka = marka
    talep.model = model
    talep.ifs_no = ifs_no
    if aciklama:
        talep.aciklama = aciklama

    if selected_type == "lisans":
        talep.tur = TalepTuru.LISANS
    elif selected_type == "envanter":
        talep.tur = TalepTuru.ENVANTER
    else:
        talep.tur = TalepTuru.AKSESUAR

    payload = {
        "is_lisans": selected_type == "lisans",
        "donanim_tipi": talep.donanim_tipi,
        "miktar": adet,
        "marka": marka,
        "model": model,
        "ifs_no": ifs_no,
        "aciklama": aciklama,
        "islem_yapan": islem_yapan,
        "source_type": f"talep:{selected_type}",
        "source_id": talep.id,
    }

    result = stock_add(payload, db)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "İşlem başarısız"))

    process_talep(talep, adet, is_cancel=False)

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
