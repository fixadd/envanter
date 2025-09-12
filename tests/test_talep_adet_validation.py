import os
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models
from routes.talepler import cancel_request, close_request
from models import Talep, TalepTuru, TalepDurum


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


@pytest.fixture()
def talep(db_session):
    t = Talep(tur=TalepTuru.AKSESUAR, miktar=5, karsilanan_miktar=0, kalan_miktar=5)
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


def test_cancel_request_zero_adet(db_session, talep):
    res = cancel_request(talep.id, adet=0, db=db_session)
    assert res.status_code == 400


def test_cancel_request_negative_adet(db_session, talep):
    res = cancel_request(talep.id, adet=-1, db=db_session)
    assert res.status_code == 400


def test_close_request_zero_adet(db_session, talep):
    res = close_request(talep.id, adet=0, db=db_session)
    assert res.status_code == 400


def test_close_request_negative_adet(db_session, talep):
    res = close_request(talep.id, adet=-3, db=db_session)
    assert res.status_code == 400


def test_kapanma_tarihi_set_on_cancel(db_session, talep):
    cancel_request(talep.id, adet=5, db=db_session)
    refreshed = db_session.get(Talep, talep.id)
    assert refreshed.durum == TalepDurum.IPTAL
    assert refreshed.kapanma_tarihi is not None


def test_kapanma_tarihi_set_on_close(db_session, talep):
    close_request(talep.id, adet=5, db=db_session)
    refreshed = db_session.get(Talep, talep.id)
    assert refreshed.durum == TalepDurum.TAMAMLANDI
    assert refreshed.kapanma_tarihi is not None
