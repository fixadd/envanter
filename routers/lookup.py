from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db  # projedeki mevcut get_db

router = APIRouter(prefix="/api/lookup", tags=["lookup"])

# Ürün Ekle sayfasındaki kartlara karşılık gelen tablolar:
# (Gerekirse tablo adlarını birebir DB'nizdeki adlarla düzeltin.)
ENTITY_TABLE = {
    "marka": "brands",
    "model": "models",           # Not: model listesi brand_id filtresi bekleyebilir.
    "fabrika": "factories",
    "kullanim-alani": "usage_areas",
    "donanim-tipi": "hardware_types",
    "lisans-adi": "license_names",
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
    db: Session = Depends(get_db),
):
    table = ENTITY_TABLE.get(entity)
    if not table:
        raise HTTPException(404, "Geçersiz entity")

    # Temel sorgu: id, ad kolonlarını bekliyoruz (modellerde marka_id var)
    params = {"limit": limit}
    where = []
    if q:
        where.append("LOWER(name) LIKE LOWER(:q)")
        params["q"] = f"%{q}%"
    if entity == "model":
        if marka_id is None:
            return []  # Model listesi marka seçimi olmadan boş dönsün
        where.append("brand_id = :brand_id")
        params["brand_id"] = marka_id

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = text(f"SELECT id, name FROM {table}{where_sql} ORDER BY name LIMIT :limit")
    rows = db.execute(sql, params).mappings().all()
    # API'ler genellikle {id, name} döndürür; "text" gibi farklı anahtarlar
    # istemcilerde karışıklığa yol açıyordu. Tutarlılık için "name" alanı
    # döndürüyoruz ve eski "text" beklentisi olan istemcilerde de sorun
    # yaşanmaması için çağrı tarafında gerekli uyarlamayı yapıyoruz.
    return [{"id": r["id"], "name": r["name"]} for r in rows]


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
    return [r["value"] for r in rows if (r["value"] or "").strip()]
