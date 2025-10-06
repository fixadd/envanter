# routers/refdata.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db

# MODELLER: şemanla aynı olsun
from models import Brand  # brands
from models import Factory  # factories
from models import HardwareType  # hardware_types
from models import LicenseName  # license_names
from models import Model  # models (FK: brand_id)
from models import UsageArea  # usage_areas

router = APIRouter(prefix="/api/ref", tags=["refdata"])


class RefCreate(BaseModel):
    name: str
    brand_id: int | None = None  # sadece model için gerekir


ENTITY = {
    "fabrika": {"model": Factory, "name_col": "name"},
    "kullanim-alani": {"model": UsageArea, "name_col": "name"},
    "donanim-tipi": {"model": HardwareType, "name_col": "name"},
    "marka": {"model": Brand, "name_col": "name"},
    "model": {"model": Model, "name_col": "name", "brand_fk": "brand_id"},
    "lisans-adi": {"model": LicenseName, "name_col": "name"},
}


@router.post("/{entity}")
def create_ref(entity: str, body: RefCreate, db: Session = Depends(get_db)):
    cfg = ENTITY.get(entity)
    if not cfg:
        raise HTTPException(404, "Geçersiz entity")

    ModelCls = cfg["model"]
    name_col = getattr(ModelCls, cfg["name_col"])

    # MODEL -> brand_id zorunlu
    if entity == "model":
        brand_fk = cfg["brand_fk"]
        if not body.brand_id:
            raise HTTPException(400, "Model eklemek için brand_id gerekli")
        # aynı marka altında aynı model ismi tekrar eklenmesin
        exists = (
            db.query(ModelCls)
            .filter(func.lower(name_col) == body.name.strip().lower())
            .filter(getattr(ModelCls, brand_fk) == body.brand_id)
            .first()
        )
        if exists:
            return {
                "id": exists.id,
                "name": getattr(exists, cfg["name_col"]),
                "created": False,
            }
        obj = ModelCls(**{cfg["name_col"]: body.name.strip(), brand_fk: body.brand_id})

    else:
        # Diğer referanslar (name unique)
        exists = (
            db.query(ModelCls)
            .filter(func.lower(name_col) == body.name.strip().lower())
            .first()
        )
        if exists:
            return {
                "id": exists.id,
                "name": getattr(exists, cfg["name_col"]),
                "created": False,
            }
        obj = ModelCls(**{cfg["name_col"]: body.name.strip()})

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"id": obj.id, "name": getattr(obj, cfg["name_col"]), "created": True}
