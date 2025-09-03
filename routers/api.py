from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from sqlalchemy import func, case, and_, or_
from typing import List

router = APIRouter(prefix="/api", tags=["API"])

# Basit lookup tablosu
ENTITY_TABLE = {
    "donanim_tipi": models.HardwareType,
    "kullanim_alani": models.UsageArea,
    "license_names": models.LicenseName,  # lisans adlarını ayrı tabloda tutuyorsan
    "marka": models.Brand,
    "model": models.Model,
}


@router.get("/lookup/{entity}", response_model=List[str])
def lookup_entity(entity: str, db: Session = Depends(get_db)):
    entity = entity.strip().lower()
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


@router.get("/licenses/list")
def licenses_list(db: Session = Depends(get_db)):
    rows = (
        db.query(models.License)
        .filter(models.License.durum != "hurda")
        .order_by(models.License.id.asc())
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "lisans_adi": r.lisans_adi,
                "lisans_anahtari": r.lisans_anahtari,
            }
            for r in rows
        ]
    }


@router.get("/printers/list")
def printers_list(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Printer)
        .filter(models.Printer.durum != "hurda")
        .order_by(models.Printer.id.asc())
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "marka": r.marka,
                "model": r.model,
                "seri_no": r.seri_no,
            }
            for r in rows
        ]
    }


@router.get("/users/list")
def users_list(
    q: str | None = None,
    role: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.User)
    if q:
        like = f"%{q}%"
        filters = [models.User.username.ilike(like)]
        if hasattr(models.User, "full_name"):
            filters.append(models.User.full_name.ilike(like))
        if hasattr(models.User, "first_name"):
            filters.append(models.User.first_name.ilike(like))
        if hasattr(models.User, "last_name"):
            filters.append(models.User.last_name.ilike(like))
        query = query.filter(or_(*filters))
    if role:
        query = query.filter(models.User.role == role)
    rows = query.order_by(models.User.id.asc()).all()
    return {
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "full_name": getattr(u, "full_name", None),
                "email": u.email,
                "role": u.role,
            }
            for u in rows
        ]
    }


@router.get("/inventory/list")
def inventory_list(
    q: str | None = None,
    fabrika: str | None = None,
    departman: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Inventory).filter(models.Inventory.durum != "hurda")
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Inventory.no.ilike(like),
                models.Inventory.sorumlu_personel.ilike(like),
                models.Inventory.marka.ilike(like),
                models.Inventory.model.ilike(like),
                models.Inventory.bilgisayar_adi.ilike(like),
                models.Inventory.seri_no.ilike(like),
                models.Inventory.ifs_no.ilike(like),
            )
        )
    if fabrika:
        query = query.filter(models.Inventory.fabrika == fabrika)
    if departman:
        query = query.filter(models.Inventory.departman == departman)
    rows = query.order_by(models.Inventory.id.desc()).all()
    return {"items": [r.to_dict() for r in rows]}


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
    assign = models.StockAssignment(
        donanim_tipi=donanim_tipi,
        miktar=miktar,
        ifs_no=ifs_no,
        hedef_envanter_no=hedef_envanter_no,
        sorumlu_personel=sorumlu_personel,
        kullanim_alani=kullanim_alani,
        actor=islem_yapan,
    )
    db.add(assign)
    target = None
    if hedef_tur == "lisans":
        target = db.query(models.License).filter_by(ifs_no=ifs_no).first()
        if not target:
            raise HTTPException(404, "Lisans bulunamadı")
        if hedef_envanter_no:
            target.bagli_envanter_no = hedef_envanter_no
        if sorumlu_personel:
            target.sorumlu_personel = sorumlu_personel
    elif hedef_tur == "envanter":
        target = db.query(models.Inventory).filter_by(no=hedef_envanter_no).first()
        if not target:
            raise HTTPException(404, "Envanter bulunamadı")
        if ifs_no:
            target.ifs_no = ifs_no
        if sorumlu_personel:
            target.sorumlu_personel = sorumlu_personel
        if kullanim_alani:
            target.kullanim_alani = kullanim_alani
    elif hedef_tur == "yazici":
        target = db.query(models.Printer).filter_by(ifs_no=ifs_no).first()
        if not target:
            raise HTTPException(404, "Yazıcı bulunamadı")
        if sorumlu_personel:
            target.sorumlu_personel = sorumlu_personel
        if kullanim_alani:
            target.kullanim_alani = kullanim_alani
        if hedef_envanter_no:
            target.envanter_no = hedef_envanter_no
            target.bagli_envanter_no = hedef_envanter_no
    db.commit()
    log = (
        db.query(models.StockLog)
        .order_by(models.StockLog.id.desc())
        .first()
    )
    if not log or log.donanim_tipi != donanim_tipi or log.miktar != miktar or log.ifs_no != ifs_no or log.islem != "cikti":
        raise HTTPException(500, "Log kaydı doğrulanamadı")
    return {
        "ok": True,
        "donanim_tipi": donanim_tipi,
        "miktar": miktar,
        "ifs_no": ifs_no,
    }

