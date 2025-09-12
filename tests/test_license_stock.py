import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models
from routers.license import stock_license

import pytest


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def test_stock_license_updates_total(db_session):
    db = db_session
    lic = models.License(
        lisans_adi="Office",
        ifs_no="IFS-L1",
        lisans_anahtari="KEY",
        mail_adresi="x@example.com",
    )
    db.add(lic)
    db.commit()

    user = SimpleNamespace(username="tester")
    stock_license(lic.id, db=db, user=user)

    total = db.get(models.StockTotal, "Office")
    assert total is not None
    assert total.toplam == 1
    log = db.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log.donanim_tipi == "Office"
    assert log.miktar == 1
    assert log.islem == "girdi"
    assert log.ifs_no == "IFS-L1"
