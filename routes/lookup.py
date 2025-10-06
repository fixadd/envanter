from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_db
from models import Lookup

router = APIRouter(prefix="/api/lookup", tags=["Lookup"])


class LookupIn(BaseModel):
    value: str


@router.get("/{type}")
def list_lookup(type: str, db: Session = Depends(get_db)):
    rows = (
        db.query(Lookup).filter(Lookup.type == type).order_by(Lookup.value.asc()).all()
    )
    return [{"id": r.id, "value": r.value} for r in rows]


@router.post("/{type}")
def create_lookup(type: str, body: LookupIn, db: Session = Depends(get_db)):
    v = (body.value or "").strip()
    if not v:
        raise HTTPException(status_code=400, detail="Boş değer")
    exists = db.query(Lookup).filter(Lookup.type == type, Lookup.value == v).first()
    if exists:
        return {"id": exists.id, "value": exists.value}
    row = Lookup(type=type, value=v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "value": row.value}


@router.delete("/{type}/{id}")
def delete_lookup(type: str, id: int, db: Session = Depends(get_db)):
    row = db.query(Lookup).filter(Lookup.id == id, Lookup.type == type).first()
    if not row:
        raise HTTPException(status_code=404, detail="Bulunamadı")
    db.delete(row)
    db.commit()
    return {"ok": True}
