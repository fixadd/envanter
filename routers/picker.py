from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from database import get_db
from models import UsageArea, LicenseName, Factory, HardwareType, Brand, Model

router = APIRouter(prefix="/api/picker", tags=["Picker"])

ENTITY_MAP = {
    "kullanim_alani": {"model": UsageArea, "label": "name"},
    "lisans_adi": {"model": LicenseName, "label": "name"},
    "fabrika": {"model": Factory, "label": "name"},
    "donanim_tipi": {"model": HardwareType, "label": "name"},
    "marka": {"model": Brand, "label": "name"},
    "model": {"model": Model, "label": "name"},
}


def resolve_entity(entity: str):
    meta = ENTITY_MAP.get(entity)
    if not meta or meta["model"] is None:
        raise HTTPException(status_code=404, detail="Entity bulunamadı / modellenmedi.")
    return meta


@router.get("/{entity}", response_model=List[Dict[str, Any]])
def picker_list(
    entity: str,
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    meta = resolve_entity(entity)
    ModelCls = meta["model"]
    label = meta["label"]
    query = db.query(ModelCls)
    if q:
        query = query.filter(getattr(ModelCls, label).ilike(f"%{q}%"))
    rows = query.order_by(getattr(ModelCls, label).asc()).limit(200).all()
    return [{"id": getattr(r, "id"), "text": getattr(r, label)} for r in rows]


@router.delete("/{entity}/{row_id}")
def picker_delete(entity: str, row_id: int, db: Session = Depends(get_db)):
    meta = resolve_entity(entity)
    ModelCls = meta["model"]
    obj = db.get(ModelCls, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    db.delete(obj)
    db.commit()
    return {"ok": True}
