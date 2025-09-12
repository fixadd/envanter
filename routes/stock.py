from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from database import get_db
from models import HardwareType, StockTransaction

router = APIRouter(prefix="/api/stock", tags=["stock"])


def stock_query(db: Session):
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
        db.query(
            HardwareType.id.label("donanim_tipi_id"),
            func.coalesce(HardwareType.name, StockTransaction.donanim_tipi).label(
                "donanim_tipi"
            ),
            net_expr,
            hurda_expr,
        )
        .select_from(StockTransaction)
        .outerjoin(HardwareType, HardwareType.name == StockTransaction.donanim_tipi)
        .group_by(
            HardwareType.id, HardwareType.name, StockTransaction.donanim_tipi
        )
        .order_by(func.coalesce(HardwareType.name, StockTransaction.donanim_tipi).asc())
    )
    return q


@router.get("/state")
def get_stock_state(db: Session = Depends(get_db)):
    rows = stock_query(db).all()
    return {
        "items": [
            {
                "donanim_tipi_id": r.donanim_tipi_id,
                "donanim_tipi": r.donanim_tipi,
                "stok": int(r.stok or 0),
                "hurda": int(r.hurda or 0),
            }
            for r in rows
        ]
    }


@router.get("/state/debug")
def get_stock_state_debug(db: Session = Depends(get_db)):
    counts = (
        db.query(
            StockTransaction.islem,
            func.count(1).label("adet"),
            func.coalesce(func.sum(StockTransaction.miktar), 0).label("toplam"),
        )
        .group_by(StockTransaction.islem)
        .all()
    )
    return {
        "hareket_ozet": [
            {
                "islem": c.islem,
                "adet": int(c.adet),
                "toplam": int(c.toplam or 0),
            }
            for c in counts
        ]
    }

