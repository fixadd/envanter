# scripts/seed_minimal.py
# Hızlı demo verileri: kullanıcılar + referans tablolar (marka, model, fabrika, kullanım alanı, donanım tipi, lisans adı)
# python -m scripts.seed_minimal

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import SessionLocal  # repo mevcut dosyalar
import models  # tablolar burada


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
    db = SessionLocal()
    try:
        # 1) Kullanıcılar (full_name dolu olmalı)
        # Not: Parola hash'ini repo'daki user creation flow'u zaten üretiyor olabilir;
        # burada demo amaçlı basit şifre yazıyoruz. Prod'da paneli kullan.
        if hasattr(models, "User"):
            # aynı username varsa güncelle, yoksa ekle
            upsert_one(db, models.User,
                       {"username": "kadir"},
                       {"full_name": "Kadir Can", "role": "user", "password_hash": "demo"})
            upsert_one(db, models.User,
                       {"username": "mehmet"},
                       {"full_name": "Mehmet Yılmaz", "role": "user", "password_hash": "demo"})

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
                upsert_one(db, models.Model, {"brand_id": hp_id, "name": "LaserJet 1020"}, {})
            if canon_id:
                upsert_one(db, models.Model, {"brand_id": canon_id, "name": "LBP631C"}, {})

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
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
