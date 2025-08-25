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
    if entity == "model" and marka_id:
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
