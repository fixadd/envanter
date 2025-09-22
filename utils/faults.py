from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import (
    FaultRecord,
    Inventory,
    InventoryLog,
    License,
    LicenseLog,
    Printer,
    PrinterHistory,
)

ENTITY_ALIASES = {
    "inventory": "inventory",
    "envanter": "inventory",
    "inventories": "inventory",
    "lisans": "license",
    "license": "license",
    "licenses": "license",
    "yazici": "printer",
    "printer": "printer",
    "printers": "printer",
    "stok": "stock",
    "stock": "stock",
}

ENTITY_MODELS = {
    "inventory": Inventory,
    "license": License,
    "printer": Printer,
}

FAULT_STATUS_OPEN = "arızalı"
FAULT_STATUS_REPAIRED = "tamir_edildi"
FAULT_STATUS_SCRAP = "hurda"


def normalize_entity(entity: str) -> str:
    key = (entity or "").strip().lower()
    if key not in ENTITY_ALIASES:
        raise ValueError(f"Unsupported entity type: {entity}")
    return ENTITY_ALIASES[key]


def _meta_to_text(meta: Optional[dict[str, Any]]) -> Optional[str]:
    if not meta:
        return None
    try:
        return json.dumps(meta, ensure_ascii=False)
    except (TypeError, ValueError):
        return None


def _meta_from_text(meta_text: Optional[str]) -> dict[str, Any] | None:
    if not meta_text:
        return None
    try:
        return json.loads(meta_text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def get_open_fault(
    db: Session,
    entity: str,
    *,
    entity_id: Optional[int] = None,
    entity_key: Optional[str] = None,
) -> Optional[FaultRecord]:
    entity_name = normalize_entity(entity)
    query = (
        db.query(FaultRecord)
        .filter(FaultRecord.entity_type == entity_name)
        .filter(FaultRecord.status == FAULT_STATUS_OPEN)
    )
    if entity_id is not None:
        query = query.filter(FaultRecord.entity_id == entity_id)
    elif entity_key:
        query = query.filter(FaultRecord.entity_key == entity_key)
    else:
        raise ValueError("entity_id or entity_key must be provided")
    return query.order_by(FaultRecord.created_at.desc()).first()


def mark_fault(
    db: Session,
    entity: str,
    *,
    entity_id: Optional[int] = None,
    entity_key: Optional[str] = None,
    device_no: Optional[str] = None,
    title: Optional[str] = None,
    reason: str = "",
    destination: str = "",
    actor: str = "",
    meta: Optional[dict[str, Any]] = None,
) -> FaultRecord:
    entity_name = normalize_entity(entity)
    key = entity_key or (str(entity_id) if entity_id is not None else None)
    if entity_id is None and not key:
        raise ValueError("entity_id or entity_key must be provided")
    record = get_open_fault(
        db, entity_name, entity_id=entity_id, entity_key=key
    )
    if record is None:
        record = FaultRecord(
            entity_type=entity_name,
            entity_id=entity_id,
            entity_key=key,
            created_by=actor or None,
            created_at=datetime.utcnow(),
        )
    record.entity_id = entity_id
    record.entity_key = key
    record.device_no = device_no or record.device_no or key
    record.title = title or record.title or record.device_no or key
    record.reason = reason
    record.destination = destination
    record.status = FAULT_STATUS_OPEN
    record.meta = _meta_to_text(meta)
    record.updated_at = datetime.utcnow()
    record.resolved_at = None
    record.resolved_by = None
    record.note = None
    db.add(record)

    model = ENTITY_MODELS.get(entity_name)
    if model and entity_id is not None:
        item = db.get(model, entity_id)
        if not item:
            raise ValueError("Kayıt bulunamadı")
        before_status = getattr(item, "durum", None)
        if hasattr(item, "durum"):
            item.durum = FAULT_STATUS_OPEN
            db.add(item)
        log_reason = reason or "Arıza bildirimi"
        if entity_name == "inventory":
            db.add(
                InventoryLog(
                    inventory_id=item.id,
                    action="fault",
                    before_json={"durum": before_status} if before_status else None,
                    after_json={
                        "durum": FAULT_STATUS_OPEN,
                        "reason": log_reason,
                        "destination": destination or "",
                    },
                    note="Arızalı olarak işaretlendi",
                    actor=actor,
                    created_at=datetime.utcnow(),
                )
            )
        elif entity_name == "license":
            db.add(
                LicenseLog(
                    license_id=item.id,
                    islem="ARIZA",
                    detay=f"Arıza: {log_reason}; Gönderildiği: {destination or '-'}",
                    islem_yapan=actor,
                    tarih=datetime.utcnow(),
                )
            )
        elif entity_name == "printer":
            db.add(
                PrinterHistory(
                    printer_id=item.id,
                    action="fault",
                    changes={
                        "durum": {"old": before_status, "new": FAULT_STATUS_OPEN},
                        "reason": {"old": None, "new": log_reason},
                        "destination": {"old": None, "new": destination or ""},
                    },
                    actor=actor,
                    created_at=datetime.utcnow(),
                )
            )
    return record


def resolve_fault(
    db: Session,
    entity: str,
    *,
    entity_id: Optional[int] = None,
    entity_key: Optional[str] = None,
    status: str = FAULT_STATUS_REPAIRED,
    actor: str = "",
    note: str = "",
) -> Optional[FaultRecord]:
    entity_name = normalize_entity(entity)
    key = entity_key or (str(entity_id) if entity_id is not None else None)
    if entity_id is None and not key:
        raise ValueError("entity_id or entity_key must be provided")
    record = get_open_fault(
        db, entity_name, entity_id=entity_id, entity_key=key
    )
    if record is None:
        return None

    record.status = status
    record.resolved_at = datetime.utcnow()
    record.resolved_by = actor or None
    record.updated_at = datetime.utcnow()
    record.note = note or record.note
    db.add(record)

    model = ENTITY_MODELS.get(entity_name)
    if model and entity_id is not None:
        item = db.get(model, entity_id)
        if item and hasattr(item, "durum"):
            before_status = getattr(item, "durum", None)
            if status == FAULT_STATUS_REPAIRED:
                item.durum = "aktif"
                log_note = "Arıza giderildi"
            elif status == FAULT_STATUS_SCRAP:
                item.durum = FAULT_STATUS_SCRAP
                log_note = "Arıza kaydı hurdaya taşındı"
            else:
                item.durum = status
                log_note = note or "Arıza kaydı güncellendi"
            db.add(item)

            if entity_name == "inventory":
                db.add(
                    InventoryLog(
                        inventory_id=item.id,
                        action="repair" if status == FAULT_STATUS_REPAIRED else "fault_close",
                        before_json={"durum": before_status} if before_status else None,
                        after_json={"durum": item.durum},
                        note=log_note,
                        actor=actor,
                        created_at=datetime.utcnow(),
                    )
                )
            elif entity_name == "license":
                db.add(
                    LicenseLog(
                        license_id=item.id,
                        islem="TAMIR" if status == FAULT_STATUS_REPAIRED else "ARIZA_KAPAT",
                        detay=log_note,
                        islem_yapan=actor,
                        tarih=datetime.utcnow(),
                    )
                )
            elif entity_name == "printer":
                db.add(
                    PrinterHistory(
                        printer_id=item.id,
                        action="repair" if status == FAULT_STATUS_REPAIRED else "fault_close",
                        changes={
                            "durum": {"old": before_status, "new": item.durum},
                        },
                        actor=actor,
                        created_at=datetime.utcnow(),
                    )
                )
    return record


def serialize_fault(record: FaultRecord) -> dict[str, Any]:
    data = record.to_dict()
    data["meta"] = _meta_from_text(record.meta)
    data["created_at"] = record.created_at.isoformat() if record.created_at else None
    data["updated_at"] = record.updated_at.isoformat() if record.updated_at else None
    data["resolved_at"] = record.resolved_at.isoformat() if record.resolved_at else None
    return data
