from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from sqlalchemy import func, case, and_

router = APIRouter(prefix="/api", tags=["API"])

# Basit lookup tablosu
ENTITY_TABLE = {
    # "donanim_tipi": models.HardwareType,
    # "kullanim_alani": models.UsageArea,
    # "license_names": models.LicenseName,  # lisans adlarını ayrı tabloda tutuyorsan
}


@router.get("/lookup/{entity}")
def lookup_entity(entity: str, db: Session = Depends(get_db)):
    tbl = ENTITY_TABLE.get(entity)
    if not tbl:
        raise HTTPException(status_code=404, detail="Entity not found")
    rows = db.query(tbl.name).order_by(tbl.name.asc()).all()
    return [r[0] for r in rows if r[0]]


@router.get("/users/names")
def user_names(db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.full_name.asc()).all()
    return [u.full_name for u in users if u.full_name]


@router.get("/licenses/names")
def license_names(db: Session = Depends(get_db)):
    if hasattr(models, "LicenseName"):
        rows = db.query(models.LicenseName.name).order_by(models.LicenseName.name.asc()).all()
        return [r[0] for r in rows if r[0]]
    rows = db.query(models.License.lisans_adi).distinct().order_by(models.License.lisans_adi.asc()).all()
    return [r[0] for r in rows if r[0]]


@router.get("/printers/models")
def printer_models(brand: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    if not hasattr(models, "Model"):
        raise HTTPException(status_code=500, detail="Model tablosu tanımlı değil")
    rows = (
        db.query(models.Model.name)
        .join(models.Brand, models.Model.brand_id == models.Brand.id)
        .filter(models.Brand.name == brand)
        .order_by(models.Model.name.asc())
        .all()
    )
    return [r[0] for r in rows if r[0]]


# === STOCK API ===
@router.get("/stock/status")
def stock_status(db: Session = Depends(get_db)):
    totals = {t.donanim_tipi: t.toplam for t in db.query(models.StockTotal).all()}
    q = (
        db.query(
            models.StockLog.donanim_tipi,
            models.StockLog.ifs_no,
            func.sum(
                case(
                    (models.StockLog.islem == "girdi", models.StockLog.miktar),
                    else_=-models.StockLog.miktar,
                )
            ).label("qty"),
        )
        .group_by(models.StockLog.donanim_tipi, models.StockLog.ifs_no)
    )
    detail: dict[str, dict[str, int]] = {}
    for dt, ifs, qty in q:
        if ifs and qty and qty > 0:
            detail.setdefault(dt, {})[ifs] = qty
    return {"totals": totals, "detail": detail}


@router.post("/stock/logs")
def stock_log_create(
    donanim_tipi: str,
    miktar: int,
    islem: str,
    ifs_no: str | None = None,
    islem_yapan: str | None = None,
    db: Session = Depends(get_db),
):
    if islem not in ("girdi", "cikti", "hurda"):
        raise HTTPException(400, "Geçersiz işlem")
    if miktar <= 0:
        raise HTTPException(400, "Miktar > 0 olmalı")
    total = db.get(models.StockTotal, donanim_tipi) or models.StockTotal(
        donanim_tipi=donanim_tipi, toplam=0
    )
    if islem in ("cikti", "hurda") and total.toplam < miktar:
        raise HTTPException(400, "Yetersiz stok")
    log = models.StockLog(
        donanim_tipi=donanim_tipi,
        miktar=miktar,
        islem=islem,
        ifs_no=ifs_no,
        actor=islem_yapan,
    )
    db.add(log)
    total.toplam = total.toplam + miktar if islem == "girdi" else total.toplam - miktar
    db.merge(total)
    db.commit()
    return {"ok": True}


@router.post("/stock/assign")
def stock_assign(
    donanim_tipi: str,
    miktar: int,
    hedef_tur: str,
    ifs_no: str | None = None,
    hedef_envanter_no: str | None = None,
    sorumlu_personel: str | None = None,
    kullanim_alani: str | None = None,
    islem_yapan: str | None = None,
    db: Session = Depends(get_db),
):
    if hedef_tur not in ("envanter", "lisans", "yazici"):
        raise HTTPException(400, "Geçersiz hedef_tur")
    status = stock_status(db)
    mevcut = status["totals"].get(donanim_tipi, 0)
    if mevcut < miktar:
        raise HTTPException(400, "Yetersiz stok")
    if not ifs_no:
        adaylar = status["detail"].get(donanim_tipi, {})
        if len(adaylar) == 1:
            ifs_no = next(iter(adaylar.keys()))
        elif len(adaylar) > 1:
            raise HTTPException(400, "Birden fazla IFS bulundu, seçim gerekli")
    _ = stock_log_create(
        donanim_tipi,
        miktar,
        "cikti",
        ifs_no=ifs_no,
        islem_yapan=islem_yapan,
        db=db,
    )
    # TODO: hedef_tur'a göre ilişki tablosuna ekle
    return {"ok": True, "donanim_tipi": donanim_tipi, "miktar": miktar, "ifs_no": ifs_no}

