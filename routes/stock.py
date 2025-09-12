from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from database import get_db
from models import StockTransaction

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/state")
def get_stock_state(db: Session = Depends(get_db)):
    net_expr = func.sum(
        case(
            (StockTransaction.islem == "girdi", StockTransaction.miktar),
            (StockTransaction.islem == "cikti", -StockTransaction.miktar),
            else_=0,
        )
    ).label("stok")

    hurda_expr = func.sum(
        case((StockTransaction.islem == "hurda", StockTransaction.miktar), else_=0)
    ).label("hurda")

    q = (
        db.query(StockTransaction.donanim_tipi.label("donanim_tipi"), net_expr, hurda_expr)
        .group_by(StockTransaction.donanim_tipi)
        .order_by(StockTransaction.donanim_tipi.asc())
    )
    rows = q.all()

    return {
        "items": [
            {
                "donanim_tipi": r.donanim_tipi,
                "stok": int(r.stok or 0),
                "hurda": int(r.hurda or 0),
            }
            for r in rows
        ]
    }
