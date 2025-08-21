# routers/requests.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def list_requests(request: Request):
    return templates.TemplateResponse("requests/list.html", {"request": request})

@router.get("/create", response_class=HTMLResponse)
async def create_request(request: Request):
    return templates.TemplateResponse("requests/create.html", {"request": request})

@router.get("/convert/{request_id}", response_class=HTMLResponse)
async def convert_request(request_id: int, request: Request):
    return templates.TemplateResponse("requests/convert.html", {"request": request, "request_id": request_id})
