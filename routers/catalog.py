from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_db
from models import Brand, Model

router = APIRouter(prefix="/catalog", tags=["Katalog"])

@router.get("/brands")
def list_brands(db: Session = Depends(get_db)):
    items = db.query(Brand).order_by(Brand.name.asc()).all()
    return [{"id": b.id, "name": b.name} for b in items]

@router.get("/models")
def list_models(brand_id: int, db: Session = Depends(get_db)):
    items = (
        db.query(Model)
        .filter(Model.brand_id == brand_id)
        .order_by(Model.name.asc())
        .all()
    )
    return [{"id": m.id, "name": m.name} for m in items]

@router.post("/brands")
def create_brand(name: str, db: Session = Depends(get_db)):
    name = (name or "").strip()
    if not name:
        raise HTTPException(400, "Marka adı boş olamaz")
    exists = db.query(Brand).filter(Brand.name.ilike(name)).first()
    if exists:
        return {"ok": True, "id": exists.id}
    b = Brand(name=name)
    db.add(b)
    db.commit()
    return {"ok": True, "id": b.id}

@router.post("/models")
def create_model(brand_id: int, name: str, db: Session = Depends(get_db)):
    name = (name or "").strip()
    if not name:
        raise HTTPException(400, "Model adı boş olamaz")
    brand = db.query(Brand).get(brand_id)
    if not brand:
        raise HTTPException(404, "Marka yok")
    exists = (
        db.query(Model)
        .filter(Model.brand_id == brand_id, Model.name.ilike(name))
        .first()
    )
    if exists:
        return {"ok": True, "id": exists.id}
    m = Model(brand_id=brand_id, name=name)
    db.add(m)
    db.commit()
    return {"ok": True, "id": m.id}
