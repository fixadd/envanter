from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from auth import get_db
from models import Factory, UsageArea, HardwareType, Brand, Model, LicenseName

router = APIRouter(prefix="/api/ref", tags=["refdata"])


class RefCreate(BaseModel):
    ad: str
    marka_id: int | None = None  # model için


ENTITY_MAP = {
    "fabrika": Factory,
    "kullanim-alani": UsageArea,
    "donanim-tipi": HardwareType,
    "marka": Brand,
    "model": Model,
    "lisans-adi": LicenseName,
}


@router.post("/{entity}")
def create_ref(entity: str, body: RefCreate, db: Session = Depends(get_db)):
    ModelCls = ENTITY_MAP.get(entity)
    if not ModelCls:
        raise HTTPException(404, "Geçersiz entity")

    q = db.query(ModelCls).filter(func.lower(ModelCls.name) == body.ad.strip().lower())
    if entity == "model":
        if not body.marka_id:
            raise HTTPException(400, "model için marka_id gerekli")
        q = q.filter(Model.brand_id == body.marka_id)

    obj = q.first()
    if obj:
        return {"id": obj.id, "ad": getattr(obj, "name", None), "created": False}

    if entity == "model":
        obj = Model(name=body.ad.strip(), brand_id=body.marka_id)
    else:
        obj = ModelCls(name=body.ad.strip())

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": obj.id, "ad": getattr(obj, "name", None), "created": True}
