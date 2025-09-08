from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import cast, Integer

from database import get_db
from models import Talep, TalepTuru, TalepDurum, HardwareType, Brand, Model

router = APIRouter(prefix="/api/talep", tags=["Talep"])

@router.post("/ekle")
def talep_ekle(item: dict, db: Session = Depends(get_db)):
    rec = Talep(
        tur=TalepTuru.AKSESUAR,
        ifs_no=item.get("ifs_no"),
        donanim_tipi=item.get("donanim_tipi_id"),
        marka=item.get("marka_id"),
        model=item.get("model_id"),
        miktar=item.get("miktar"),
        aciklama=item.get("aciklama"),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"ok": True, "id": rec.id}

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
