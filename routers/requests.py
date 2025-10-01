# routers/requests.py
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Integer, cast
from sqlalchemy.orm import Session

from database import get_db
from models import Brand, HardwareType, Model, Talep, TalepDurum, TalepTuru
from utils.requests_export import export_requests_workbook

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/export")
async def export_requests(db: Session = Depends(get_db)):
    """Export request records as an Excel file."""
    headers = [
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
        "Bağlı Envanter",
        "Lisans Adı",
        "Sorumlu",
        "Açıklama",
        "Durum",
        "Tarih",
    ]

    rows = db.query(Talep).all()

    def build_row(talep: Talep):
        return [
            talep.id,
            talep.tur.value,
            talep.donanim_tipi or "",
            talep.ifs_no or "",
            talep.miktar or "",
            talep.karsilanan_miktar or "",
            talep.kalan_miktar or "",
            talep.marka or "",
            talep.model or "",
            talep.envanter_no or "",
            talep.bagli_envanter_no or "",
            talep.lisans_adi or "",
            talep.sorumlu_personel or "",
            talep.aciklama or "",
            talep.durum.value,
            talep.olusturma_tarihi.strftime("%Y-%m-%d %H:%M"),
        ]

    return export_requests_workbook(rows, headers, build_row)


@router.post("/import", response_class=PlainTextResponse)
async def import_requests(file: UploadFile = File(...)):
    return f"Received {file.filename}, but import is not implemented."


def _list_by_status(db: Session, durum: TalepDurum):
    q = (
        db.query(
            Talep,
            HardwareType.name.label("donanim_tipi_name"),
            Brand.name.label("marka_name"),
            Model.name.label("model_name"),
        )
        .outerjoin(HardwareType, HardwareType.id == cast(Talep.donanim_tipi, Integer))
        .outerjoin(Brand, Brand.id == cast(Talep.marka, Integer))
        .outerjoin(Model, Model.id == cast(Talep.model, Integer))
        .filter(Talep.durum == durum)
        .order_by(Talep.ifs_no.asc(), Talep.id.asc())
    )
    rows = []
    for t, dt_name, marka_name, model_name in q.all():
        t.donanim_tipi = dt_name or t.donanim_tipi
        t.marka = marka_name or t.marka
        t.model = model_name or t.model
        rows.append(t)
    return rows


@router.get("/", response_class=HTMLResponse)
async def list_requests(request: Request, db: Session = Depends(get_db)):
    """Display requests grouped by status."""

    acik = _list_by_status(db, TalepDurum.ACIK)
    kapali = _list_by_status(db, TalepDurum.TAMAMLANDI)
    iptal = _list_by_status(db, TalepDurum.IPTAL)

    return templates.TemplateResponse(
        "requests/list.html",
        {
            "request": request,
            "acik": acik,
            "kapali": kapali,
            "iptal": iptal,
        },
    )


@router.post("/", response_class=JSONResponse)
async def create_request(
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
    return {"ok": True, "id": talep.id}


@router.get("/create", response_class=HTMLResponse)
async def create_request_form(request: Request):
    return templates.TemplateResponse("requests/create.html", {"request": request})


@router.get("/convert/{request_id}", response_class=HTMLResponse)
async def convert_request(request_id: int, request: Request):
    return templates.TemplateResponse(
        "requests/convert.html", {"request": request, "request_id": request_id}
    )
