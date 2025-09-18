import asyncio
import os, sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import models
from models import StockLog

from routers.stock import export_stock, stock_status, stock_status_json


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


def test_stock_status_json_is_serializable(db_session):
    db_session.add(StockLog(donanim_tipi='monitor', marka='dell', model='u2412', ifs_no='ifs-2', miktar=3, islem='girdi', tarih=datetime.utcnow()))
    db_session.commit()

    payload = stock_status_json(db_session)
    assert payload['ok'] is True
    assert payload['totals']
    assert payload['items']
    item = payload['items'][0]
    assert item['donanim_tipi'] == 'monitor'
    assert item['net_miktar'] == 3


def test_export_stock_uses_status_rows(db_session):
    db_session.add(StockLog(donanim_tipi='laptop', marka='asus', model='a110', ifs_no='ifs', miktar=4, islem='girdi', tarih=datetime.utcnow()))
    db_session.add(StockLog(donanim_tipi='laptop', marka='asus', model='a110', ifs_no='ifs', miktar=1, islem='cikti', tarih=datetime.utcnow()))
    db_session.commit()

    async def run_export():
        response = await export_stock(db_session)
        body = b''.join([chunk async for chunk in response.body_iterator])
        return response, body

    response, body = asyncio.run(run_export())

    wb = load_workbook(BytesIO(body))
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    assert rows[0] == ('Donanım Tipi', 'Marka', 'Model', 'IFS No', 'Stok', 'Son İşlem', 'Kaynak Türü', 'Kaynak ID')
    assert rows[1][0:5] == ('laptop', 'asus', 'a110', 'ifs', 3)
    assert isinstance(rows[1][5], str) and rows[1][5]
