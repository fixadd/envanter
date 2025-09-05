import os
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models
from routes.talepler import convert_request_to_stock
from models import Talep, TalepTuru, TalepDurum, StockLog, StockTotal


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def test_convert_request_to_stock_creates_log_and_closes(db_session):
    talep = Talep(
        tur=TalepTuru.AKSESUAR,
        donanim_tipi="mouse",
        miktar=5,
        marka="Logi",
        model="M185",
        ifs_no="123",
    )
    db_session.add(talep)
    db_session.commit()
    db_session.refresh(talep)

    res = convert_request_to_stock(talep.id, adet=5, islem_yapan="tester", db=db_session)
    assert res["ok"] is True

    log = db_session.query(StockLog).first()
    assert log.donanim_tipi == "mouse"
    assert log.miktar == 5
    assert log.ifs_no == "123"
    assert log.marka == "Logi"
    assert log.model == "M185"
    assert log.islem == "girdi"
    assert log.actor == "tester"

    total = db_session.get(StockTotal, "mouse")
    assert total.toplam == 5

    refreshed = db_session.get(Talep, talep.id)
    assert refreshed.durum == TalepDurum.TAMAMLANDI
    assert refreshed.miktar == 0
    assert refreshed.kapanma_tarihi is not None
