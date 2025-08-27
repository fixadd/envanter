from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from database import get_db
from models import UsageArea, LicenseName, Factory, HardwareType, Brand, Model

router = APIRouter(prefix="/api/picker", tags=["Picker"])

# --- MODEL eşleme ---
# label: görünen metnin alanı
# parent_field: (opsiyonel) bağlı fk alanı (ör. model.brand_id)
ENTITY_MAP = {
    "kullanim_alani": {"model": UsageArea, "label": "name", "parent_field": None},
    "lisans_adi":     {"model": LicenseName, "label": "name", "parent_field": None},
    "fabrika":        {"model": Factory, "label": "name", "parent_field": None},
    "donanim_tipi":   {"model": HardwareType, "label": "name", "parent_field": None},
    "marka":          {"model": Brand, "label": "name", "parent_field": None},
    "model":          {"model": Model, "label": "name", "parent_field": "brand_id"},  # 🔴 bağlı
}

def resolve_entity(entity: str):
    meta = ENTITY_MAP.get(entity)
    if not meta or meta["model"] is None:
        raise HTTPException(404, "Entity bulunamadı / modellenmedi.")
    return meta

class CreatePayload(BaseModel):
    text: str
    parent_id: Optional[int] = None  # (örn. model eklerken marka_id)

@router.get("/{entity}", response_model=List[Dict[str, Any]])
def picker_list(
    entity: str,
    q: Optional[str] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    meta = resolve_entity(entity)
    Model = meta["model"]
    label = meta["label"]
    parent_field = meta.get("parent_field")

    query = db.query(Model)

    # parent filter: ?marka_id=.. veya ?parent_id=..
    params = dict(request.query_params)
    raw_parent = params.get("parent_id") or params.get("marka_id")
    if parent_field and not raw_parent:
        raw_parent = params.get(parent_field)
    if parent_field and raw_parent:
        query = query.filter(getattr(Model, parent_field) == int(raw_parent))

    if q:
        query = query.filter(getattr(Model, label).ilike(f"%{q}%"))

    rows = query.order_by(getattr(Model, label).asc()).limit(200).all()
    return [{"id": getattr(r, "id"), "text": getattr(r, label)} for r in rows]

@router.post("/{entity}", response_model=Dict[str, Any])
def picker_create(entity: str, body: CreatePayload, db: Session = Depends(get_db)):
    meta = resolve_entity(entity)
    Model = meta["model"]
    label = meta["label"]
    parent_field = meta.get("parent_field")

    # Boş/çok kısa kontrolü
    name = (body.text or "").strip()
    if not name:
        raise HTTPException(400, "Metin gerekli.")

    # Duplicate basit kontrol (case-insensitive)
    exists_q = db.query(Model).filter(getattr(Model, label).ilike(name))
    if parent_field and body.parent_id:
        exists_q = exists_q.filter(getattr(Model, parent_field) == body.parent_id)
    if db.query(exists_q.exists()).scalar():
        raise HTTPException(409, "Kayıt zaten var.")

    kwargs = {label: name}
    if parent_field and body.parent_id:
        kwargs[parent_field] = body.parent_id

    obj = Model(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": getattr(obj, "id"), "text": getattr(obj, label)}

@router.delete("/{entity}/{row_id}")
def picker_delete(entity: str, row_id: int, db: Session = Depends(get_db)):
    meta = resolve_entity(entity)
    Model = meta["model"]
    obj = db.query(Model).get(row_id)
    if not obj:
        raise HTTPException(404, "Kayıt bulunamadı.")
    db.delete(obj)
    db.commit()
    return {"ok": True}
