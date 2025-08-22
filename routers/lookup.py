from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from auth import get_db
from models import Factory, UsageArea, HardwareType, Brand, Model, LicenseName

router = APIRouter(prefix="/api/lookup", tags=["lookup"])

ENTITY_MAP = {
    "fabrika": Factory,
    "kullanim-alani": UsageArea,
    "donanim-tipi": HardwareType,
    "marka": Brand,
    "model": Model,
    "lisans-adi": LicenseName,
}


@router.get("/{entity}")
def lookup_list(
    entity: str,
    q: str = Query(""),
    limit: int = 30,
    marka_id: int | None = None,
    db: Session = Depends(get_db),
):
    ModelCls = ENTITY_MAP.get(entity)
    if not ModelCls:
        raise HTTPException(404, "Geçersiz entity")

    query = db.query(ModelCls)
    if entity == "model" and marka_id:
        query = query.filter(Model.brand_id == marka_id)

    if q:
        query = query.filter(func.lower(ModelCls.name).contains(q.lower()))

    rows = query.order_by(ModelCls.name).limit(limit).all()
    return [{"id": r.id, "ad": getattr(r, "name", None)} for r in rows]
