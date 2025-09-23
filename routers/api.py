from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from sqlalchemy import func, case, or_, literal
from typing import List

from utils.stock_log import create_stock_log, get_available_columns, normalize_islem

router = APIRouter(prefix="/api", tags=["API"])

# Basit lookup tablosu
ENTITY_TABLE = {
    "donanim_tipi": models.HardwareType,
    "kullanim_alani": models.UsageArea,
    "license_names": models.LicenseName,  # lisans adlarını ayrı tabloda tutuyorsan
    "marka": models.Brand,
    "model": models.Model,
}


@router.get("/lookup_plain/{entity}", response_model=List[str])
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
@router.get("/stock/detail")
def stock_status_detail(db: Session = Depends(get_db)):
    """Return current stock grouped by item details."""

    totals_db = {t.donanim_tipi: t.toplam for t in db.query(models.StockTotal).all()}

    available_columns = set(get_available_columns(db))
    if not available_columns:
        available_columns = {col.name for col in models.StockLog.__table__.columns}

    has_marka = "marka" in available_columns
    has_model = "model" in available_columns
    has_ifs_no = "ifs_no" in available_columns
    has_source_type = "source_type" in available_columns
    has_source_id = "source_id" in available_columns
    has_lisans_key = "lisans_anahtari" in available_columns
    has_mail = "mail_adresi" in available_columns

    q = (
        db.query(
            models.StockLog.donanim_tipi,
            (models.StockLog.marka if has_marka else literal(None)).label("marka"),
            (models.StockLog.model if has_model else literal(None)).label("model"),
            (models.StockLog.ifs_no if has_ifs_no else literal(None)).label("ifs_no"),
            func.sum(
                case(
                    (models.StockLog.islem == "girdi", models.StockLog.miktar),
                    else_=-models.StockLog.miktar,
                )
            ).label("qty"),
            func.max(models.StockLog.tarih).label("last_tarih"),
        )
    )

    group_cols = [models.StockLog.donanim_tipi]
    if has_marka:
        group_cols.append(models.StockLog.marka)
    if has_model:
        group_cols.append(models.StockLog.model)
    if has_ifs_no:
        group_cols.append(models.StockLog.ifs_no)

    q = q.group_by(*group_cols)

    rows = q.all()

    # Determine the source of the last movement for each item
    last_logs_query = db.query(
        models.StockLog.donanim_tipi,
        (models.StockLog.marka if has_marka else literal(None)).label("marka"),
        (models.StockLog.model if has_model else literal(None)).label("model"),
        (models.StockLog.ifs_no if has_ifs_no else literal(None)).label("ifs_no"),
        (
            models.StockLog.source_type if has_source_type else literal(None)
        ).label("source_type"),
        (
            models.StockLog.source_id if has_source_id else literal(None)
        ).label("source_id"),
        (
            models.StockLog.lisans_anahtari
            if has_lisans_key
            else literal(None)
        ).label("lisans_anahtari"),
        (
            models.StockLog.mail_adresi if has_mail else literal(None)
        ).label("mail_adresi"),
        models.StockLog.tarih,
        models.StockLog.id,
    )

    order_cols = [models.StockLog.donanim_tipi]
    if has_marka:
        order_cols.append(models.StockLog.marka)
    if has_model:
        order_cols.append(models.StockLog.model)
    if has_ifs_no:
        order_cols.append(models.StockLog.ifs_no)
    order_cols.extend([models.StockLog.tarih.desc(), models.StockLog.id.desc()])

    last_logs = last_logs_query.order_by(*order_cols).all()


    last_source: dict[
        tuple[str, str | None, str | None, str | None],
        dict[str, str | int | None],
    ] = {}
    for r in last_logs:
        key = (r.donanim_tipi, r.marka, r.model, r.ifs_no)
        if key not in last_source:
            last_source[key] = {
                "source_type": r.source_type,
                "source_id": r.source_id,
                "lisans_anahtari": r.lisans_anahtari,
                "mail_adresi": r.mail_adresi,
            }

    items: list[dict] = []
    totals_calc: dict[str, int] = {}

    for r in rows:
        qty = int(r.qty or 0)
        if qty <= 0:
            continue
        key = (r.donanim_tipi, r.marka, r.model, r.ifs_no)
        src = last_source.get(key, {})
        items.append(
            {
                "donanim_tipi": r.donanim_tipi,
                "marka": r.marka,
                "model": r.model,
                "ifs_no": r.ifs_no,
                "net": qty,
                "last_tarih": r.last_tarih,
                "source_type": src.get("source_type"),
                "source_id": src.get("source_id"),
                "lisans_anahtari": src.get("lisans_anahtari"),
                "mail_adresi": src.get("mail_adresi"),
            }
        )
        totals_calc[r.donanim_tipi] = totals_calc.get(r.donanim_tipi, 0) + qty

    totals = totals_db or totals_calc
    return {"totals": totals, "items": items}


@router.post("/stock/logs")
def stock_log_create(
    donanim_tipi: str,
    miktar: int,
    islem: str,
    ifs_no: str | None = None,
    islem_yapan: str | None = None,
    aciklama: str | None = None,
    db: Session = Depends(get_db),
):
    islem_normalized, islem_valid = normalize_islem(islem)
    if not islem_valid:
        raise HTTPException(400, "Geçersiz işlem")
    if miktar <= 0:
        raise HTTPException(400, "Miktar > 0 olmalı")
    total = db.get(models.StockTotal, donanim_tipi) or models.StockTotal(
        donanim_tipi=donanim_tipi, toplam=0
    )
    if islem_normalized in ("cikti", "hurda", "atama") and total.toplam < miktar:
        raise HTTPException(400, "Yetersiz stok")
    create_stock_log(
        db,
        donanim_tipi=donanim_tipi,
        miktar=miktar,
        islem=islem_normalized,
        ifs_no=ifs_no,
        actor=islem_yapan,
        aciklama=aciklama,
    )
    if islem_normalized == "girdi":
        total.toplam += miktar
    else:
        total.toplam -= miktar
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
    aciklama: str | None = None,
    db: Session = Depends(get_db),
):
    if hedef_tur not in ("envanter", "lisans", "yazici"):
        raise HTTPException(400, "Geçersiz hedef_tur")
    status = stock_status_detail(db)
    mevcut = status["totals"].get(donanim_tipi, 0)
    if ifs_no:
        for r in status["items"]:
            if r["donanim_tipi"] == donanim_tipi and r.get("ifs_no") == ifs_no:
                mevcut = r["net"]
                break
    else:
        adaylar = [r for r in status["items"] if r["donanim_tipi"] == donanim_tipi]
        if len(adaylar) == 1:
            ifs_no = adaylar[0]["ifs_no"]
            mevcut = adaylar[0]["net"]
        elif len(adaylar) > 1:
            raise HTTPException(400, "Birden fazla IFS bulundu, seçim gerekli")
    if mevcut < miktar:
        raise HTTPException(400, "Yetersiz stok")
    _ = stock_log_create(
        donanim_tipi,
        miktar,
        "cikti",
        ifs_no=ifs_no,
        islem_yapan=islem_yapan,
        aciklama=aciklama,
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

