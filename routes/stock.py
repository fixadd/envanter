from fastapi import APIRouter, Depends, Body, Request
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import StockLog, StockAssignment, License, Inventory, Printer

router = APIRouter(prefix="/stock", tags=["Stock"])

@router.post("/add")
def stock_add(payload: dict = Body(...), db: Session = Depends(get_db)):
    log = StockLog(
        donanim_tipi = payload.get("donanim_tipi"),
        miktar       = int(payload.get("miktar") or 0),
        ifs_no       = payload.get("ifs_no") or None,
        islem        = payload.get("islem") or "girdi",
        tarih        = datetime.utcnow(),
        actor        = payload.get("islem_yapan") or "Sistem",
    )
    db.add(log)
    db.commit()
    return {"ok": True, "id": log.id}

@router.post("/assign")
def stock_assign(payload: dict = Body(...), db: Session = Depends(get_db)):
    target_type = payload.get("targetType")
    now = datetime.utcnow()
    desc = None
    if target_type == "license":
        lic_id = payload.get("license_id")
        lic = db.query(License).get(int(lic_id)) if lic_id else None
        if not lic:
            return {"ok": False, "error": "Lisans bulunamadı"}
        desc = f"Lisans envantere atandı"
    elif target_type == "inventory":
        inv_id = payload.get("inventory_id")
        inv = db.query(Inventory).get(int(inv_id)) if inv_id else None
        if not inv:
            return {"ok": False, "error": "Envanter bulunamadı"}
        desc = f"Stok envantere atandı"
    elif target_type == "printer":
        prn_id = payload.get("printer_id")
        prn = db.query(Printer).get(int(prn_id)) if prn_id else None
        if not prn:
            return {"ok": False, "error": "Yazıcı bulunamadı"}
        desc = f"Stok yazıcıya atandı"
    else:
        return {"ok": False, "error": "Geçersiz hedef"}

    assign = StockAssignment(
        donanim_tipi = payload.get("donanim_tipi"),
        miktar = int(payload.get("miktar") or 0),
        ifs_no = payload.get("ifs_no") or None,
        hedef_envanter_no = payload.get("inventory_id") or None,
        actor = payload.get("islem_yapan") or "Sistem",
        tarih = now,
    )
    db.add(assign)
    db.add(StockLog(
        donanim_tipi=assign.donanim_tipi,
        miktar=assign.miktar,
        ifs_no=assign.ifs_no,
        islem="atama",
        actor=assign.actor,
        tarih=now,
    ))
    db.commit()
    return {"ok": True, "desc": desc}
