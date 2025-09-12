import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models
from routers.inventory import stock_entry
from routers.printers import stock_printer

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


def test_inventory_stock_source(db_session):
    inv = models.Inventory(
        no="E1",
        donanim_tipi="Laptop",
        marka="Dell",
        model="X",
        ifs_no="IFS1",
    )
    db_session.add(inv)
    db_session.commit()

    user = SimpleNamespace(username="tester")
    stock_entry(inv.id, db=db_session, user=user)

    log = db_session.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log.source_type == "envanter"
    assert log.source_id == inv.id


def test_printer_stock_source(db_session):
    p = models.Printer(
        marka="HP",
        model="P100",
        ifs_no="PRN1",
    )
    db_session.add(p)
    db_session.commit()

    user = SimpleNamespace(username="tester")
    stock_printer(p.id, db=db_session, user=user)

    log = db_session.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log.source_type == "yazici"
    assert log.source_id == p.id

