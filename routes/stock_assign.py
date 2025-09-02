from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Literal

from database import get_db
from models import StockTotal, StockLog, Inventory, License, Printer
from routers.api import stock_status


router = APIRouter(prefix="/stock", tags=["StockAssign"])


class StockOption(BaseModel):
    """UI'daki stok seçenekleri için DTO."""

    id: str
    label: str
    donanim_tipi: Optional[str] = None
    ifs_no: Optional[str] = None
    mevcut_miktar: int


class AssignPayload(BaseModel):
    """Stok atama isteği."""

    stock_id: str = Field(..., description="donanim_tipi|ifs_no biçiminde kimlik")
    atama_turu: Literal["lisans", "envanter", "yazici"]
    miktar: int = 1

    hedef_envanter_id: Optional[int] = None
    hedef_yazici_id: Optional[int] = None
    lisans_id: Optional[int] = None
    sorumlu_personel_id: Optional[str] = None
    notlar: Optional[str] = None


@router.get("/options", response_model=list[StockOption])
def stock_options(db: Session = Depends(get_db), q: Optional[str] = None):
    """Miktarı > 0 olan stokları döndür."""

    status = stock_status(db)
    items: list[StockOption] = []
    q_lower = q.lower() if q else None

    for dt, total in status["totals"].items():
        detail = status["detail"].get(dt, {})
        if detail:
            for ifs, qty in detail.items():
                if qty <= 0:
                    continue
                if q_lower and q_lower not in dt.lower() and q_lower not in (ifs or "").lower():
                    continue
                items.append(
                    StockOption(
                        id=f"{dt}|{ifs}",
                        label=f"{dt or 'Donanım'} | IFS:{ifs or '-'} | Mevcut:{qty}",
                        donanim_tipi=dt,
                        ifs_no=ifs,
                        mevcut_miktar=qty,
                    )
                )
        elif total > 0:
            if q_lower and q_lower not in dt.lower():
                continue
            items.append(
                StockOption(
                    id=f"{dt}|",
                    label=f"{dt or 'Donanım'} | IFS:- | Mevcut:{total}",
                    donanim_tipi=dt,
                    mevcut_miktar=total,
                )
            )

    return items


@router.post("/assign")
def stock_assign(payload: AssignPayload, db: Session = Depends(get_db)):
    """Stoktaki bir kaydı lisans/envanter/yazıcıya atar."""

    try:
        donanim_tipi, ifs_no = payload.stock_id.split("|", 1)
    except ValueError:  # pragma: no cover - validation
        raise HTTPException(status_code=400, detail="Geçersiz stok kimliği.")
    ifs_no = ifs_no or None

    status = stock_status(db)
    mevcut = status["detail"].get(donanim_tipi, {}).get(ifs_no)
    if mevcut is None:
        mevcut = status["totals"].get(donanim_tipi, 0)

    if payload.miktar <= 0:
        raise HTTPException(status_code=400, detail="Miktar 0'dan büyük olmalı.")
    if payload.miktar > mevcut:
        raise HTTPException(
            status_code=400,
            detail="Stoktaki mevcut miktardan fazla atayamazsınız.",
        )

    personel = payload.sorumlu_personel_id

    if payload.atama_turu == "envanter":
        if not payload.hedef_envanter_id:
            raise HTTPException(status_code=422, detail="Hedef envanter seçiniz.")
        hedef = db.get(Inventory, payload.hedef_envanter_id)
        if not hedef:
            raise HTTPException(status_code=404, detail="Hedef envanter bulunamadı.")
        if ifs_no:
            hedef.ifs_no = ifs_no
        if personel:
            hedef.sorumlu_personel = personel
    elif payload.atama_turu == "yazici":
        if not payload.hedef_yazici_id:
            raise HTTPException(status_code=422, detail="Hedef yazıcı seçiniz.")
        hedef = db.get(Printer, payload.hedef_yazici_id)
        if not hedef:
            raise HTTPException(status_code=404, detail="Hedef yazıcı bulunamadı.")
        if personel:
            hedef.sorumlu_personel = personel
    elif payload.atama_turu == "lisans":
        if not payload.lisans_id:
            raise HTTPException(status_code=422, detail="Lisans seçiniz.")
        hedef = db.get(License, payload.lisans_id)
        if not hedef:
            raise HTTPException(status_code=404, detail="Lisans bulunamadı.")
        if personel:
            hedef.sorumlu_personel = personel
        if payload.hedef_envanter_id:
            env = db.get(Inventory, payload.hedef_envanter_id)
            if env:
                hedef.bagli_envanter_no = env.no
    else:  # pragma: no cover - validation
        raise HTTPException(status_code=400, detail="Geçersiz atama türü.")

    total = db.get(StockTotal, donanim_tipi)
    if not total or total.toplam < payload.miktar:
        raise HTTPException(status_code=400, detail="Yetersiz stok.")

    total.toplam -= payload.miktar
    db.merge(total)

    db.add(
        StockLog(
            donanim_tipi=donanim_tipi,
            miktar=payload.miktar,
            ifs_no=ifs_no,
            islem="cikti",
            actor=personel,
        )
    )

    db.commit()

    return {
        "ok": True,
        "message": "Atama tamamlandı.",
        "kalan_miktar": total.toplam,
    }

