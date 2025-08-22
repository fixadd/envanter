# routers/lookup.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from database import get_db

# MODELLER: depodaki models.py'deki sınıf adlarıyla birebir eşleşmeli
from models import Fabrika, KullanimAlani, DonanimTipi, Marka, Model, LisansAdi

router = APIRouter(prefix="/api/lookup", tags=["lookup"])

ENTITY_MODEL = {
    "fabrika": Fabrika,
    "kullanim-alani": KullanimAlani,
    "donanim-tipi": DonanimTipi,
    "marka": Marka,
    "model": Model,
    "lisans-adi": LisansAdi,
}

def _name_column(cls):
    """
    Modellerdeki 'ad' alanı bazı repolarda 'adi' veya 'name' olabiliyor.
    Güvenli şekilde kolon adını belirleyelim.
    """
    for cand in ("ad", "adi", "name", "isim", "title"):
        if hasattr(cls, cand):
            return getattr(cls, cand)
    raise AttributeError(f"{cls.__name__} için ad/name kolonu bulunamadı")

@router.get("/{entity}")
def lookup_list(
    entity: str,
    q: str = Query(""),
    limit: int = 50,
    marka_id: int | None = None,
    db: Session = Depends(get_db),
):
    ModelCls = ENTITY_MODEL.get(entity)
    if not ModelCls:
        raise HTTPException(404, "Geçersiz entity")

    name_col = _name_column(ModelCls)
    stmt = select(ModelCls.id, name_col).order_by(name_col).limit(limit)

    # marka → model bağımlılığı
    if entity == "model" and marka_id:
        stmt = stmt.where(Model.marka_id == marka_id)

    # arama
    if q:
        stmt = stmt.where(func.lower(name_col).like(func.lower(f"%{q}%")))

    try:
        rows = db.execute(stmt).all()
    except Exception as e:
        # Hatanın nedenini loglayalım ve 400 döndürelim ki frontend 500 görmesin
        # (uvicorn logunda stacktrace'i göreceksin)
        raise HTTPException(status_code=400, detail=f"lookup hata: {type(e).__name__}: {e}")

    # JSON
    return [{"id": r[0], "ad": r[1]} for r in rows]
