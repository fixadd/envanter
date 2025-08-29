# routers/requests.py
from fastapi import APIRouter, Request, UploadFile, File, Depends, Form
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    StreamingResponse,
    JSONResponse,
)
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from fastapi.templating import Jinja2Templates
from models import Talep, TalepTuru, TalepDurum

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/export")
async def export_requests(db: Session = Depends(get_db)):
    """Export request records as an Excel file."""
    from openpyxl import Workbook
    from io import BytesIO

    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "ID",
            "Tür",
            "Donanım Tipi",
            "IFS No",
            "Marka",
            "Model",
            "Miktar",
            "Envanter No",
            "Bağlı Envanter",
            "Lisans Adı",
            "Sorumlu",
            "Açıklama",
            "Durum",
            "Tarih",
        ]
    )

    for t in db.query(Talep).all():
        ws.append(
            [
                t.id,
                t.tur.value,
                t.donanim_tipi or "",
                t.ifs_no or "",
                t.marka or "",
                t.model or "",
                t.miktar or "",
                t.envanter_no or "",
                t.bagli_envanter_no or "",
                t.lisans_adi or "",
                t.sorumlu_personel or "",
                t.aciklama or "",
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


@router.post("/import", response_class=PlainTextResponse)
async def import_requests(file: UploadFile = File(...)):
    return f"Received {file.filename}, but import is not implemented."


@router.get("/", response_class=HTMLResponse)
async def list_requests(request: Request, db: Session = Depends(get_db)):
    def group(rows: list[Talep]) -> dict[str, list[Talep]]:
        gruplu: dict[str, list[Talep]] = {}
        for t in rows:
            key = t.ifs_no or f"NO-IFS-{t.id}"
            gruplu.setdefault(key, []).append(t)
        return gruplu

    aktif = group(
        db.query(Talep).filter(Talep.durum == TalepDurum.AKTIF).all()
    )
    kapali = group(
        db.query(Talep).filter(Talep.durum == TalepDurum.TAMAMLANDI).all()
    )
    iptal = group(
        db.query(Talep).filter(Talep.durum == TalepDurum.IPTAL).all()
    )

    return templates.TemplateResponse(
        "requests/list.html",
        {
            "request": request,
            "gruplu_aktif": aktif,
            "gruplu_kapali": kapali,
            "gruplu_iptal": iptal,
        },
    )


@router.post("/", response_class=JSONResponse)
async def create_request(
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
    return {"ok": True, "id": talep.id}


@router.get("/create", response_class=HTMLResponse)
async def create_request_form(request: Request):
    return templates.TemplateResponse("requests/create.html", {"request": request})


@router.get("/convert/{request_id}", response_class=HTMLResponse)
async def convert_request(request_id: int, request: Request):
    return templates.TemplateResponse(
        "requests/convert.html", {"request": request, "request_id": request_id}
    )
