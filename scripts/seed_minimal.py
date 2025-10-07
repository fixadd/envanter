# scripts/seed_minimal.py
# Hızlı demo verileri: kullanıcılar + referans tablolar (marka, model, fabrika, kullanım alanı, donanım tipi, lisans adı)
# python -m scripts.seed_minimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import models  # tablolar burada
from app.core.security import hash_password, is_password_hash
from database import SessionLocal  # repo mevcut dosyalar


def upsert_one(db: Session, model, where: dict, values: dict):
    obj = db.execute(select(model).filter_by(**where)).scalars().first()
    if obj:
        for k, v in values.items():
            setattr(obj, k, v)
        db.add(obj)
        return obj
    obj = model(**{**where, **values})
    db.add(obj)
    return obj


def main():
    models.init_db()
    db = SessionLocal()
    try:
        # 1) Kullanıcılar (full_name dolu olmalı)
        if hasattr(models, "User"):
            for username, full_name in ("kadir", "Kadir Can"), ("mehmet", "Mehmet Yılmaz"):
                user = db.execute(
                    select(models.User).filter_by(username=username)
                ).scalars().first()
                if user is None:
                    db.add(
                        models.User(
                            username=username,
                            full_name=full_name,
                            role="user",
                            password_hash=hash_password("demo"),
                        )
                    )
                else:
                    user.full_name = full_name
                    user.role = "user"
                    if not is_password_hash(user.password_hash):
                        user.password_hash = hash_password("demo")
                    db.add(user)

        # 2) Referans tablolar
        # Marka
        if hasattr(models, "Brand"):
            hp = upsert_one(db, models.Brand, {"name": "HP"}, {})
            canon = upsert_one(db, models.Brand, {"name": "Canon"}, {})
            db.flush()
        # Model (brand_id ile bağlı)
        if hasattr(models, "Model"):
            hp_id = hp.id if hp else None
            canon_id = canon.id if canon else None
            if hp_id:
                upsert_one(
                    db, models.Model, {"brand_id": hp_id, "name": "LaserJet 1020"}, {}
                )
            if canon_id:
                upsert_one(
                    db, models.Model, {"brand_id": canon_id, "name": "LBP631C"}, {}
                )

        # Fabrika
        if hasattr(models, "Factory"):
            upsert_one(db, models.Factory, {"name": "Merkez"}, {})
            upsert_one(db, models.Factory, {"name": "Organize Sanayi"}, {})

        # Kullanım Alanı
        if hasattr(models, "UsageArea"):
            upsert_one(db, models.UsageArea, {"name": "Muhasebe"}, {})
            upsert_one(db, models.UsageArea, {"name": "İK"}, {})

        # Donanım Tipi
        if hasattr(models, "HardwareType"):
            upsert_one(db, models.HardwareType, {"name": "Yazıcı"}, {})
            upsert_one(db, models.HardwareType, {"name": "Bilgisayar"}, {})

        # Lisans Adı
        if hasattr(models, "LicenseName"):
            upsert_one(db, models.LicenseName, {"name": "Microsoft Office"}, {})
            upsert_one(db, models.LicenseName, {"name": "Windows Pro"}, {})

        db.commit()
        print("✅ Seed tamam: kullanıcılar ve referanslar eklendi/güncellendi.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
