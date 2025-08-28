from fastapi import APIRouter, Depends, Body, Request
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import (
    StockLog,
    StockAssignment,
    StockTotal,
    License,
    Inventory,
    Printer,
)

router = APIRouter(prefix="/stock", tags=["Stock"])

@router.post("/add")
def stock_add(payload: dict = Body(...), db: Session = Depends(get_db)):
    is_license = payload.get("is_license")
    donanim_tipi = payload.get("donanim_tipi")
    miktar = 1 if is_license else int(payload.get("miktar") or 0)
    islem = payload.get("islem") or "girdi"

    total = db.get(StockTotal, donanim_tipi) or StockTotal(
        donanim_tipi=donanim_tipi, toplam=0
    )
    if islem in ("cikti", "hurda") and total.toplam < miktar:
        return {"ok": False, "error": "Yetersiz stok"}

    log = StockLog(
        donanim_tipi=donanim_tipi,
        marka=None if is_license else payload.get("marka"),
        model=None if is_license else payload.get("model"),
        lisans_anahtari=payload.get("lisans_anahtari") if is_license else None,
        mail_adresi=payload.get("mail_adresi") if is_license else None,
        miktar=miktar,
        ifs_no=payload.get("ifs_no") or None,
        islem=islem,
        tarih=datetime.utcnow(),
        actor=payload.get("islem_yapan") or "Sistem",
    )
    db.add(log)

    total.toplam = total.toplam + miktar if islem == "girdi" else total.toplam - miktar
    db.merge(total)
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
    total = db.get(StockTotal, assign.donanim_tipi)
    if not total or total.toplam < assign.miktar:
        return {"ok": False, "error": "Yetersiz stok"}

    db.add(assign)
    db.add(
        StockLog(
            donanim_tipi=assign.donanim_tipi,
            miktar=assign.miktar,
            ifs_no=assign.ifs_no,
            islem="atama",
            actor=assign.actor,
            tarih=now,
        )
    )
    total.toplam -= assign.miktar
    db.merge(total)
    db.commit()
    return {"ok": True, "desc": desc}
