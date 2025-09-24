import os
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models
from routers.stock import stock_add


def _make_payload(**overrides):
    payload = {
        "is_lisans": False,
        "donanim_tipi": "Laptop",
        "miktar": 1,
        "islem_yapan": "tester",
        "marka": "Dell",
        "model": "X",
        "ifs_no": "IFS-1",
    }
    payload.update(overrides)
    return payload


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def test_stock_add_zero_amount(db_session):
    payload = {
        "is_lisans": False,
        "donanim_tipi": "cpu",
        "miktar": 0,
        "islem_yapan": "test",
    }
    result = stock_add(payload, db_session)
    assert result == {"ok": False, "error": "Miktar 0'dan büyük olmalı"}


def test_stock_add_negative_amount(db_session):
    payload = {
        "is_lisans": False,
        "donanim_tipi": "cpu",
        "miktar": -5,
        "islem_yapan": "test",
    }
    result = stock_add(payload, db_session)
    assert result == {"ok": False, "error": "Miktar 0'dan büyük olmalı"}


def test_stock_add_requires_type(db_session):
    payload = {"is_lisans": False, "miktar": 1, "islem_yapan": "tester"}
    result = stock_add(payload, db_session)
    assert result == {"ok": False, "error": "Donanım tipi seçiniz"}


def test_stock_add_normalizes_girdi(db_session):
    payload = _make_payload(islem="Girdi")
    result = stock_add(payload, db_session)
    assert result["ok"] is True
    log = db_session.query(models.StockLog).first()
    assert log is not None
    assert log.islem == "girdi"


def test_stock_add_normalizes_cikti_variants(db_session):
    db_session.add(models.StockTotal(donanim_tipi="Laptop", toplam=3))
    db_session.commit()

    payload = _make_payload(islem="Çıktı", miktar=2)
    result = stock_add(payload, db_session)
    assert result["ok"] is True

    log = db_session.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log is not None
    assert log.islem == "cikti"

    total = db_session.get(models.StockTotal, "Laptop")
    assert total.toplam == 1


def test_stock_add_rejects_unknown_islem(db_session):
    payload = _make_payload(islem="Bilinmeyen")
    result = stock_add(payload, db_session)
    assert result == {"ok": False, "error": "Geçersiz işlem türü"}
