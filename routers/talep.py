from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import cast, Integer
from pydantic import BaseModel, conint
from typing import List, Optional

from database import get_db
from models import Talep, TalepTuru, HardwareType, Brand, Model

router = APIRouter(prefix="/api/talep", tags=["Talep"])


class TalepLine(BaseModel):
    donanim_tipi_id: conint(gt=0)
    miktar: conint(gt=0)
    marka_id: Optional[int] = 0
    model_id: Optional[int] = 0
    aciklama: Optional[str] = None


class TalepIn(BaseModel):
    ifs_no: Optional[str] = None
    lines: List[TalepLine]


@router.post("/ekle")
def talep_ekle(item: TalepIn, db: Session = Depends(get_db)):
    if not item.lines:
        raise HTTPException(400, "Boş talep")

    ids = []
    for ln in item.lines:
        rec = Talep(
            tur=TalepTuru.AKSESUAR,
            ifs_no=item.ifs_no,
            donanim_tipi=ln.donanim_tipi_id,
            marka=ln.marka_id or None,
            model=ln.model_id or None,
            miktar=ln.miktar,
            aciklama=ln.aciklama,
        )
        db.add(rec)
        db.flush()
        ids.append(rec.id)
    db.commit()
    return {"ok": True, "ids": ids}

@router.get("/liste")
def talep_liste(db: Session = Depends(get_db)):
    q = (
        db.query(
            Talep,
            HardwareType.name.label("donanim_tipi_name"),
            Brand.name.label("marka_name"),
            Model.name.label("model_name"),
        )
        .outerjoin(HardwareType, HardwareType.id == cast(Talep.donanim_tipi, Integer))
        .outerjoin(Brand, Brand.id == cast(Talep.marka, Integer))
        .outerjoin(Model, Model.id == cast(Talep.model, Integer))
        .order_by(Talep.id.desc())
    )
    rows = []
    for t, dt_name, marka_name, model_name in q.all():
        rows.append(
            {
                "id": t.id,
                "ifs_no": t.ifs_no,
                "donanim_tipi": dt_name or t.donanim_tipi,
                "marka": marka_name or t.marka,
                "model": model_name or t.model,
                "miktar": t.miktar,
                "aciklama": t.aciklama,
                "tarih": t.olusturma_tarihi,
            }
        )
    return rows
