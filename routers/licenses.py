# routers/licenses.py
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/export", response_class=PlainTextResponse)
async def export_licenses_stub():
    return "Excel export is not implemented yet."


@router.post("/import", response_class=PlainTextResponse)
async def import_licenses_stub(file: UploadFile = File(...)):
    return f"Received {file.filename}, but import is not implemented."

@router.get("/", response_class=HTMLResponse)
async def list_licenses(request: Request):
    return templates.TemplateResponse("licenses/list.html", {"request": request})

@router.get("/assign", response_class=HTMLResponse)
async def assign_license(request: Request):
    return templates.TemplateResponse("licenses/assign.html", {"request": request})
