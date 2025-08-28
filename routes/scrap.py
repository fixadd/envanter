from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from models import StockLog

router = APIRouter()

def get_templates(request: Request):
    return request.app.state.templates

@router.get("/scrap/detail/{id}", response_class=HTMLResponse)
def scrap_detail(id: int, request: Request, db: Session = Depends(get_db)):
    row = db.query(StockLog).get(id)
    templates = get_templates(request)
    return templates.TemplateResponse("partials/scrap_detail.html", {"request": request, "row": row})
