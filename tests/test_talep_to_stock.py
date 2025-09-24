import os
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models
from routes.talepler import convert_request_to_stock
from models import Talep, TalepTuru, TalepDurum, StockLog, StockTotal
from fastapi import HTTPException


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
        karsilanan_miktar=0,
        kalan_miktar=5,
        marka="Logi",
        model="M185",
        ifs_no="123",
    )
    db_session.add(talep)
    db_session.commit()
    db_session.refresh(talep)

    res = convert_request_to_stock(
        talep.id,
        adet=5,
        islem_yapan="tester",
        aciklama="Not",
        db=db_session,
    )
    assert res["ok"] is True

    log = db_session.query(StockLog).first()
    assert log.donanim_tipi == "mouse"
    assert log.miktar == 5
    assert log.ifs_no == "123"
    assert log.marka == "Logi"
    assert log.model == "M185"
    assert log.islem == "girdi"
    assert log.actor == "tester"
    assert log.aciklama == "Not"
    assert log.source_type == "talep:envanter"
    assert log.source_id == talep.id

    total = db_session.get(StockTotal, "mouse")
    assert total.toplam == 5

    refreshed = db_session.get(Talep, talep.id)
    assert refreshed.durum == TalepDurum.TAMAMLANDI
    assert refreshed.karsilanan_miktar == 5
    assert refreshed.kalan_miktar == 0
    assert refreshed.kapanma_tarihi is not None
    assert refreshed.tur == TalepTuru.ENVANTER


def test_convert_request_requires_brand_model(db_session):
    talep = Talep(
        tur=TalepTuru.AKSESUAR,
        donanim_tipi="klavye",
        miktar=1,
        karsilanan_miktar=0,
        kalan_miktar=1,
    )
    db_session.add(talep)
    db_session.commit()
    db_session.refresh(talep)

    with pytest.raises(HTTPException) as exc:
        convert_request_to_stock(talep.id, adet=1, db=db_session)
    assert exc.value.status_code == 400

    res2 = convert_request_to_stock(
        talep.id,
        adet=1,
        marka="ABC",
        model="XYZ",
        db=db_session,
    )
    assert res2["ok"] is True

    log = db_session.query(StockLog).order_by(StockLog.id.desc()).first()
    assert log.marka == "ABC"
    assert log.model == "XYZ"
    assert log.source_type == "talep:envanter"
    assert log.source_id == talep.id


def test_convert_request_license_without_brand_model(db_session):
    talep = Talep(
        tur=TalepTuru.AKSESUAR,
        donanim_tipi="Office",
        miktar=1,
        karsilanan_miktar=0,
        kalan_miktar=1,
    )
    db_session.add(talep)
    db_session.commit()
    db_session.refresh(talep)

    res = convert_request_to_stock(
        talep.id,
        adet=1,
        tur="lisans",
        db=db_session,
    )
    assert res["ok"] is True

    log = db_session.query(StockLog).order_by(StockLog.id.desc()).first()
    assert log.donanim_tipi == "Office"
    assert log.marka is None
    assert log.model is None
    assert log.source_type == "talep:lisans"
    assert log.source_id == talep.id

    refreshed = db_session.get(Talep, talep.id)
    assert refreshed.tur == TalepTuru.LISANS
    assert refreshed.karsilanan_miktar == 1


def test_partial_convert_keeps_open(db_session):
    talep = Talep(
        tur=TalepTuru.AKSESUAR,
        donanim_tipi="klavye",
        miktar=5,
        karsilanan_miktar=0,
        kalan_miktar=5,
        marka="ABC",
        model="XYZ",
    )
    db_session.add(talep)
    db_session.commit()
    db_session.refresh(talep)

    res = convert_request_to_stock(talep.id, adet=2, db=db_session)
    assert res["ok"] is True

    refreshed = db_session.get(Talep, talep.id)
    assert refreshed.durum == TalepDurum.ACIK
    assert refreshed.karsilanan_miktar == 2
    assert refreshed.kalan_miktar == 3

    log = db_session.query(StockLog).order_by(StockLog.id.desc()).first()
    assert log.source_type == "talep:envanter"
    assert log.source_id == talep.id


def test_convert_request_printer_sets_type(db_session):
    talep = Talep(
        tur=TalepTuru.AKSESUAR,
        donanim_tipi="Yazici",
        miktar=1,
        karsilanan_miktar=0,
        kalan_miktar=1,
    )
    db_session.add(talep)
    db_session.commit()
    db_session.refresh(talep)

    res = convert_request_to_stock(
        talep.id,
        adet=1,
        tur="yazici",
        marka="HP",
        model="LaserJet",
        db=db_session,
    )
    assert res["ok"] is True

    log = db_session.query(StockLog).order_by(StockLog.id.desc()).first()
    assert log.marka == "HP"
    assert log.model == "LaserJet"
    assert log.source_type == "talep:yazici"
    assert log.source_id == talep.id

    refreshed = db_session.get(Talep, talep.id)
    assert refreshed.tur == TalepTuru.AKSESUAR
