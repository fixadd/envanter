from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from routes.stock import stock_query

templates = Jinja2Templates(directory="templates")
pages = APIRouter()


@pages.get("/stock")
def stock_page(request: Request, db: Session = Depends(get_db)):
    rows = stock_query(db).all()
    items = [
        {
            "donanim_tipi": r.donanim_tipi,
            "stok": int(r.stok or 0),
            "hurda": int(r.hurda or 0),
        }
        for r in rows
    ]
    return templates.TemplateResponse(
        "stock/index.html",
        {
            "request": request,
            "stock_items": items,
        },
    )

