from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Brand, Factory, HardwareType, LicenseName, Model, UsageArea

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


@router.get("/usage-areas")
def list_usage_areas(db: Session = Depends(get_db)):
    items = db.query(UsageArea).order_by(UsageArea.name.asc()).all()
    return [{"id": u.id, "name": u.name} for u in items]


@router.get("/factories")
def list_factories(db: Session = Depends(get_db)):
    items = db.query(Factory).order_by(Factory.name.asc()).all()
    return [{"id": f.id, "name": f.name} for f in items]


@router.get("/license-names")
def list_license_names(db: Session = Depends(get_db)):
    items = db.query(LicenseName).order_by(LicenseName.name.asc()).all()
    return [
        {"id": license_name.id, "name": license_name.name} for license_name in items
    ]


@router.get("/hardware-types")
def list_hardware_types(db: Session = Depends(get_db)):
    items = db.query(HardwareType).order_by(HardwareType.name.asc()).all()
    return [{"id": h.id, "name": h.name} for h in items]


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
    brand = db.get(Brand, brand_id)
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


@router.post("/usage-areas")
def create_usage_area(name: str, db: Session = Depends(get_db)):
    name = (name or "").strip()
    if not name:
        raise HTTPException(400, "Boş olamaz")
    exists = db.query(UsageArea).filter(UsageArea.name.ilike(name)).first()
    if exists:
        return {"ok": True, "id": exists.id}
    u = UsageArea(name=name)
    db.add(u)
    db.commit()
    return {"ok": True, "id": u.id}


@router.post("/factories")
def create_factory(name: str, db: Session = Depends(get_db)):
    name = (name or "").strip()
    if not name:
        raise HTTPException(400, "Boş olamaz")
    exists = db.query(Factory).filter(Factory.name.ilike(name)).first()
    if exists:
        return {"ok": True, "id": exists.id}
    f = Factory(name=name)
    db.add(f)
    db.commit()
    return {"ok": True, "id": f.id}


@router.post("/license-names")
def create_license_name(name: str, db: Session = Depends(get_db)):
    name = (name or "").strip()
    if not name:
        raise HTTPException(400, "Boş olamaz")
    exists = db.query(LicenseName).filter(LicenseName.name.ilike(name)).first()
    if exists:
        return {"ok": True, "id": exists.id}
    license_name = LicenseName(name=name)
    db.add(license_name)
    db.commit()
    return {"ok": True, "id": license_name.id}


@router.post("/hardware-types")
def create_hardware_type(name: str, db: Session = Depends(get_db)):
    name = (name or "").strip()
    if not name:
        raise HTTPException(400, "Boş olamaz")
    exists = db.query(HardwareType).filter(HardwareType.name.ilike(name)).first()
    if exists:
        return {"ok": True, "id": exists.id}
    h = HardwareType(name=name)
    db.add(h)
    db.commit()
    return {"ok": True, "id": h.id}
