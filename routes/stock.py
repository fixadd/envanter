from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import StockLog, StockTotal

router = APIRouter(prefix="/stock", tags=["Stock"])

@router.post("/add")
def stock_add(payload: dict = Body(...), db: Session = Depends(get_db)):
    is_license = payload.get("is_license")
    donanim_tipi = payload.get("donanim_tipi")
    miktar = 1 if is_license else int(payload.get("miktar") or 0)
    islem = payload.get("islem") or "girdi"

    total = db.get(StockTotal, donanim_tipi) or StockTotal(
        donanim_tipi=donanim_tipi, toplam=0
    )
    if islem in ("cikti", "hurda") and total.toplam < miktar:
        return {"ok": False, "error": "Yetersiz stok"}

    log = StockLog(
        donanim_tipi=donanim_tipi,
        marka=None if is_license else payload.get("marka"),
        model=None if is_license else payload.get("model"),
        lisans_anahtari=payload.get("lisans_anahtari") if is_license else None,
        mail_adresi=payload.get("mail_adresi") if is_license else None,
        miktar=miktar,
        ifs_no=payload.get("ifs_no") or None,
        islem=islem,
        tarih=datetime.utcnow(),
        actor=payload.get("islem_yapan") or "Sistem",
    )
    db.add(log)

    total.toplam = total.toplam + miktar if islem == "girdi" else total.toplam - miktar
    db.merge(total)
    db.commit()
    return {"ok": True, "id": log.id}

