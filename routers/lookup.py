from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db  # projedeki mevcut get_db
from models import Lookup, Model as ModelTbl, Brand, HardwareType

router = APIRouter(prefix="/api/lookup", tags=["lookup"])

# Basit ORM tabanlı lookup'lar

@router.get("/donanim_tipi")
def lookup_donanim_tipi(db: Session = Depends(get_db)):
    rows = db.query(HardwareType).order_by(HardwareType.name.asc()).all()
    # `adi` yerine tutarlı biçimde `name` anahtarını döndür
    return [{"id": r.id, "name": r.name} for r in rows]


@router.get("/marka")
def lookup_marka(db: Session = Depends(get_db)):
    rows = db.query(Brand).order_by(Brand.name.asc()).all()
    # İstemcilerin beklediği alan adı `name` olduğundan bu alanı döndür
    return [{"id": r.id, "name": r.name} for r in rows]


@router.get("/model")
def lookup_model(marka_id: int = Query(...), db: Session = Depends(get_db)):
    rows = (
        db.query(ModelTbl)
        .filter(ModelTbl.brand_id == marka_id)
        .order_by(ModelTbl.name.asc())
        .all()
    )
    # Tüm lookup uç noktaları aynı yapıda `id` ve `name` döndürsün
    return [{"id": r.id, "name": r.name} for r in rows]

# Ürün Ekle sayfasındaki kartlara karşılık gelen tablolar:
# (Gerekirse tablo adlarını birebir DB'nizdeki adlarla düzeltin.)
ENTITY_TABLE = {
    "marka": "brands",
    "model": "models",  # Not: model listesi brand_id filtresi bekleyebilir.
    "fabrika": "factories",
    "kullanim-alani": "usage_areas",
    "kullanim_alani": "usage_areas",
    "donanim-tipi": "hardware_types",
    "donanim_tipi": "hardware_types",
    "lisans-adi": "license_names",
    "lisans_adi": "license_names",
}

# Kolon/lookup bulunmadığında dönecek güvenli değerler
FALLBACK_LISTS = {
    "stok_durumu": ["Stokta", "Rezerve", "Atandı", "Hurda"],
    "islem": ["Girdi", "Çıktı", "Hurda"],
}

# Liste sayfalarındaki filtrelerde kullanılabilecek distinct kolon bilgileri
FILTER_MAP = {
    "inventory": {
        "table": "inventories",
        "columns": [
            "no",
            "fabrika",
            "departman",
            "sorumlu_personel",
            "marka",
            "model",
        ],
    },
    "printer": {
        "table": "printers",
        "columns": [
            "id",
            "marka",
            "model",
            "seri_no",
            "fabrika",
            "kullanim_alani",
            "sorumlu_personel",
            "bagli_envanter_no",
        ],
    },
    "license": {
        "table": "licenses",
        "columns": [
            "no",
            "lisans_adi",
            "lisans_anahtari",
            "sorumlu_personel",
            "bagli_envanter_no",
            "durum",
        ],
    },
}

@router.get("/{entity}")
def lookup_list(
    entity: str,
    q: str = Query(default=""),
    limit: int = 50,
    marka_id: int | None = None,
    marka: str | None = None,
    db: Session = Depends(get_db),
):
    entity = entity.strip().lower()
    table = ENTITY_TABLE.get(entity)

    if table:
        # Temel sorgu: id, ad kolonlarını bekliyoruz (modellerde marka_id var)
        params = {"limit": limit}
        where = []
        if q:
            where.append("LOWER(name) LIKE LOWER(:q)")
            params["q"] = f"%{q}%"
        if entity == "model":
            if marka_id is None and marka:
                try:
                    row = db.execute(
                        text("SELECT id FROM brands WHERE name = :name LIMIT 1"),
                        {"name": marka},
                    ).mappings().first()
                    if row:
                        marka_id = row["id"]
                except Exception:
                    pass
            if marka_id is None:
                return []  # Model listesi marka seçimi olmadan boş dönsün
            where.append("brand_id = :brand_id")
            params["brand_id"] = marka_id

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        sql = text(
            f"SELECT id, name FROM {table}{where_sql} ORDER BY name LIMIT :limit"
        )
        rows = db.execute(sql, params).mappings().all()
        # API'ler genellikle {id, name} döndürür; "text" gibi farklı anahtarlar
        # istemcilerde karışıklığa yol açıyordu. Tutarlılık için "name" alanı
        # döndürüyoruz ve eski "text" beklentisi olan istemcilerde de sorun
        # yaşanmaması için çağrı tarafında gerekli uyarlamayı yapıyoruz.
        return [{"id": r["id"], "name": r["name"]} for r in rows]

    # Kolon bazlı tablo yoksa Lookup.type tablosunu dene
    try:
        q_expr = db.query(Lookup.value).filter(Lookup.type == entity)
        if q:
            q_expr = q_expr.filter(Lookup.value.ilike(f"%{q}%"))
        q_expr = q_expr.order_by(Lookup.value.asc()).limit(limit)
        rows = [r[0] for r in q_expr.all() if r and r[0]]
        if rows:
            return rows
    except Exception:
        pass

    # Kolon yoksa veya boş döndüyse: fallback listesi varsa onu döndür
    if entity in FALLBACK_LISTS:
        return FALLBACK_LISTS[entity]

    raise HTTPException(404, "Geçersiz entity")


@router.get("/distinct/{entity}/{column}", name="lookup.distinct")
def distinct_values(entity: str, column: str, db: Session = Depends(get_db)):
    cfg = FILTER_MAP.get(entity)
    if not cfg or column not in cfg["columns"]:
        raise HTTPException(404, "Geçersiz entity/kolon")
    sql = text(
        f"SELECT DISTINCT {column} AS value FROM {cfg['table']} "
        f"WHERE {column} IS NOT NULL ORDER BY {column}"
    )
    rows = db.execute(sql).mappings().all()
    values = []
    for r in rows:
        value = r["value"]
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        values.append(value)
    return values
