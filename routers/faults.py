from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import FaultRecord
from security import current_user
from utils.faults import (
    FAULT_STATUS_OPEN,
    FAULT_STATUS_REPAIRED,
    FAULT_STATUS_SCRAP,
    get_open_fault,
    mark_fault,
    normalize_entity,
    resolve_fault,
    serialize_fault,
)

router = APIRouter(prefix="/faults", tags=["Faults"])

STATUS_ALIASES = {
    "open": FAULT_STATUS_OPEN,
    "arızalı": FAULT_STATUS_OPEN,
    "arizali": FAULT_STATUS_OPEN,
    "tamir": FAULT_STATUS_REPAIRED,
    "tamir_edildi": FAULT_STATUS_REPAIRED,
    "repair": FAULT_STATUS_REPAIRED,
    "hurda": FAULT_STATUS_SCRAP,
    "scrap": FAULT_STATUS_SCRAP,
}


@router.get("/list")
def list_faults(
    entity: str = Query(..., description="Modül adı (envanter, lisans, yazıcı, stok)"),
    status: str = Query(FAULT_STATUS_OPEN, description="Filtrelenecek durum"),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    entity_name = normalize_entity(entity)
    status_name = STATUS_ALIASES.get(status.lower(), status)
    query = db.query(FaultRecord).filter(FaultRecord.entity_type == entity_name)
    if status_name:
        query = query.filter(FaultRecord.status == status_name)
    records = query.order_by(FaultRecord.created_at.desc()).all()
    items = [serialize_fault(rec) for rec in records]
    return {"items": items, "count": len(items)}


@router.get("/entity")
def fault_for_entity(
    entity: str = Query(..., description="Modül"),
    entity_id: int | None = Query(None),
    entity_key: str | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    try:
        record = get_open_fault(
            db,
            entity,
            entity_id=entity_id,
            entity_key=entity_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if record is None:
        return {"fault": None}
    return {"fault": serialize_fault(record)}


@router.post("/mark")
def mark_fault_endpoint(
    entity: str = Form(...),
    entity_id: int | None = Form(None),
    entity_key: str = Form(""),
    device_no: str = Form(""),
    title: str = Form(""),
    reason: str = Form(""),
    destination: str = Form(""),
    meta: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    actor = getattr(user, "full_name", None) or getattr(user, "username", "")
    try:
        meta_obj = json.loads(meta) if meta else None
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Geçersiz ek veri")

    try:
        record = mark_fault(
            db,
            entity,
            entity_id=entity_id,
            entity_key=entity_key or None,
            device_no=device_no or None,
            title=title or None,
            reason=reason,
            destination=destination,
            actor=actor,
            meta=meta_obj,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    return JSONResponse({"ok": True, "record": serialize_fault(record)})


@router.post("/repair")
def repair_fault_endpoint(
    entity: str = Form(...),
    entity_id: int | None = Form(None),
    entity_key: str = Form(""),
    status: str = Form(FAULT_STATUS_REPAIRED),
    note: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    actor = getattr(user, "full_name", None) or getattr(user, "username", "")
    resolved_status = STATUS_ALIASES.get(status.lower(), status)
    try:
        record = resolve_fault(
            db,
            entity,
            entity_id=entity_id,
            entity_key=entity_key or None,
            status=resolved_status,
            actor=actor,
            note=note,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    if record is None:
        raise HTTPException(status_code=404, detail="Aktif arıza kaydı bulunamadı")

    return JSONResponse({"ok": True, "record": serialize_fault(record)})
