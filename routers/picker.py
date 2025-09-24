from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db

# ==== MODELLERİNİ İMPORT ET (projeye göre güncellenmiş) ====
from models import (
    BilgiKategori,
    Brand,
    Factory,
    HardwareType,
    LicenseName,
    Lookup,
    Model,
    UsageArea,
    User,
)

router = APIRouter(prefix="/api/picker", tags=["Picker"])

# entity -> model, label, opsiyonel parent_field
ENTITY_MAP = {
    "fabrika": {"model": Factory, "label": "name", "parent_field": None},
    "kullanim_alani": {"model": UsageArea, "label": "name", "parent_field": None},
    "donanim_tipi": {"model": HardwareType, "label": "name", "parent_field": None},
    "marka": {"model": Brand, "label": "name", "parent_field": None},
    "model": {"model": Model, "label": "name", "parent_field": "brand_id"},
    "lisans_adi": {"model": LicenseName, "label": "name", "parent_field": None},
    "bilgi_kategori": {"model": BilgiKategori, "label": "ad", "parent_field": None},
    # kullanıcı ayrı ele alınacak (birden çok ad sütunu olabiliyor)
}


class CreatePayload(BaseModel):
    text: str
    parent_id: Optional[int] = None  # örn: model eklerken marka_id


def _resolve(entity: str):
    meta = ENTITY_MAP.get(entity)
    if not meta:
        raise HTTPException(404, "Entity bulunamadı.")
    return meta


# ---- KULLANICI LİSTESİ (ekleme/silme YOK) ----
@router.get("/kullanici", response_model=List[Dict[str, Any]])
def picker_users(q: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """
    User tablosundan ad soyad listeler.
    Aşağıdaki sıralı denemelerden mevcut olan alan(lar) kullanılır:
    - full_name
    - ad + soyad
    - first_name + last_name
    - name
    """
    # canditates: (column_name(s), formatter)
    candidates = []
    if hasattr(User, "full_name"):
        candidates.append(("full_name",))
    if hasattr(User, "ad") and hasattr(User, "soyad"):
        candidates.append(("ad", "soyad"))
    if hasattr(User, "first_name") and hasattr(User, "last_name"):
        candidates.append(("first_name", "last_name"))
    if hasattr(User, "name"):
        candidates.append(("name",))

    if not candidates:
        raise HTTPException(
            500,
            "User tam ad alanı bulunamadı (full_name / ad+soyad / first_name+last_name / name).",
        )

    # filtre kur: q varsa ilgili alan(lar) üzerinde ilike
    base = db.query(User)
    if q:
        ilikes = []
        for cols in candidates:
            if len(cols) == 1:
                ilikes.append(getattr(User, cols[0]).ilike(f"%{q}%"))
            else:
                # concat alanlar
                ilikes.append(
                    func.concat(
                        getattr(User, cols[0]), " ", getattr(User, cols[1])
                    ).ilike(f"%{q}%")
                )
        base = base.filter(or_(*ilikes))

    rows = base.order_by(getattr(User, candidates[0][0]).asc()).limit(200).all()

    def to_text(u):
        for cols in candidates:
            if len(cols) == 1:
                return getattr(u, cols[0])
            else:
                return f"{getattr(u, cols[0])} {getattr(u, cols[1])}"
        return str(getattr(u, "id"))

    return [{"id": getattr(u, "id"), "text": to_text(u)} for u in rows]


# ---- GENEL LİSTELEME ----
@router.get("/{entity}", response_model=List[Dict[str, Any]])
def picker_list(
    entity: str,
    q: Optional[str] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    if entity == "kullanici":
        return picker_users(q, db)  # type: ignore

    meta = _resolve(entity)
    Model = meta["model"]
    label = meta["label"]
    parent_field = meta.get("parent_field")

    query = db.query(Model)

    # parent filter: ?parent_id=.. veya entity'ye özgü param (ör. ?marka_id=..)
    params = dict(request.query_params)
    raw_parent = params.get("parent_id") or params.get("marka_id")
    if parent_field and raw_parent:
        query = query.filter(getattr(Model, parent_field) == int(raw_parent))

    if q:
        query = query.filter(getattr(Model, label).ilike(f"%{q}%"))

    rows = query.order_by(getattr(Model, label).asc()).limit(200).all()

    if not rows:
        fallback = (
            db.query(Lookup)
            .filter(Lookup.type == entity)
            .order_by(Lookup.value.asc())
            .limit(200)
            .all()
        )
        if fallback:
            return [{"id": r.id, "text": r.value} for r in fallback]

    return [{"id": getattr(r, "id"), "text": getattr(r, label)} for r in rows]


# ---- EKLE (kullanici HARİÇ) ----
@router.post("/{entity}", response_model=Dict[str, Any])
def picker_create(entity: str, body: CreatePayload, db: Session = Depends(get_db)):
    if entity == "kullanici":
        raise HTTPException(405, "Kullanıcı ekleme bu ekrandan kapalı.")

    meta = _resolve(entity)
    Model = meta["model"]
    label = meta["label"]
    parent_field = meta.get("parent_field")

    name = (body.text or "").strip()
    if not name:
        raise HTTPException(400, "Metin gerekli.")

    # parent gerektiren entity'lerde parent_id zorunlu
    if parent_field and not body.parent_id:
        raise HTTPException(400, f"{parent_field} (parent_id) gerekli.")

    # duplicate kontrol (aynı parent içinde)
    exists_q = db.query(Model).filter(
        func.lower(getattr(Model, label)) == func.lower(name)
    )
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


# ---- SİL (kullanici HARİÇ) ----
@router.delete("/{entity}/{row_id}")
def picker_delete(entity: str, row_id: int, db: Session = Depends(get_db)):
    if entity == "kullanici":
        raise HTTPException(405, "Kullanıcı silme bu ekrandan kapalı.")

    meta = _resolve(entity)
    Model = meta["model"]
    obj = db.get(Model, row_id)
    if not obj:
        raise HTTPException(404, "Kayıt bulunamadı.")
    db.delete(obj)
    db.commit()
    return {"ok": True}
