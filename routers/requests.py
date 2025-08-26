# routers/requests.py
from fastapi import APIRouter, Request, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/export")
async def export_requests(db: Session = Depends(get_db)):
    """Export request records as an Excel file."""
    from openpyxl import Workbook
    from io import BytesIO

    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Açıklama", "Durum", "Tarih"])

    # No Request model is defined yet, so this export will return only headers.

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    headers = {"Content-Disposition": "attachment; filename=requests.xlsx"}
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/import", response_class=PlainTextResponse)
async def import_requests(file: UploadFile = File(...)):
    return f"Received {file.filename}, but import is not implemented."

@router.get("/", response_class=HTMLResponse)
async def list_requests(request: Request):
    return templates.TemplateResponse("requests/list.html", {"request": request})

@router.get("/create", response_class=HTMLResponse)
async def create_request(request: Request):
    return templates.TemplateResponse("requests/create.html", {"request": request})

@router.get("/convert/{request_id}", response_class=HTMLResponse)
async def convert_request(request_id: int, request: Request):
    return templates.TemplateResponse("requests/convert.html", {"request": request, "request_id": request_id})
