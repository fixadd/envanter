import os, sys
from pathlib import Path
from datetime import datetime

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import models
from models import StockLog
from routers.stock import stock_status


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def test_stock_status_returns_rows(db_session):
    db_session.add(StockLog(donanim_tipi='laptop', marka='asus', model='a110', ifs_no='ifs', miktar=2, islem='girdi', tarih=datetime.utcnow()))
    db_session.add(StockLog(donanim_tipi='laptop', marka='asus', model='a110', ifs_no='ifs', miktar=1, islem='cikti', tarih=datetime.utcnow()))
    db_session.commit()

    rows = stock_status(db_session)
    assert rows
    row = rows[0]
    assert row['donanim_tipi'] == 'laptop'
    assert row['marka'] == 'asus'
    assert row['model'] == 'a110'
    assert row['ifs_no'] == 'ifs'
    assert row['net_miktar'] == 1
    assert row['son_islem_ts'] is not None
