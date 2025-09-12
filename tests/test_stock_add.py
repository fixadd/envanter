import os
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models
from routers.stock import stock_add


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
