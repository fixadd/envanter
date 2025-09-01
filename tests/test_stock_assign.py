import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models
from routers.api import stock_assign

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


def _setup_stock(db, donanim_tipi, toplam=5):
    db.add(models.StockTotal(donanim_tipi=donanim_tipi, toplam=toplam))
    db.commit()


def test_stock_assign_updates_license(db_session):
    db = db_session
    _setup_stock(db, "cpu")
    lic = models.License(ifs_no="IFS1")
    db.add(lic)
    db.commit()

    stock_assign(
        "cpu",
        1,
        "lisans",
        ifs_no="IFS1",
        hedef_envanter_no="INV001",
        sorumlu_personel="Ali",
        db=db,
    )

    lic = db.query(models.License).filter_by(ifs_no="IFS1").one()
    assert lic.sorumlu_personel == "Ali"
    assert lic.bagli_envanter_no == "INV001"
    log = db.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log.donanim_tipi == "cpu"
    assert log.miktar == 1
    assert log.ifs_no == "IFS1"
    assert log.islem == "cikti"
    assign = db.query(models.StockAssignment).first()
    assert assign.hedef_envanter_no == "INV001"


def test_stock_assign_updates_inventory(db_session):
    db = db_session
    _setup_stock(db, "ram")
    inv = models.Inventory(no="INV100")
    db.add(inv)
    db.commit()

    stock_assign(
        "ram",
        2,
        "envanter",
        ifs_no="IFS2",
        hedef_envanter_no="INV100",
        sorumlu_personel="Veli",
        kullanim_alani="Ofis",
        db=db,
    )

    inv = db.query(models.Inventory).filter_by(no="INV100").one()
    assert inv.ifs_no == "IFS2"
    assert inv.sorumlu_personel == "Veli"
    assert inv.kullanim_alani == "Ofis"
    log = db.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log.donanim_tipi == "ram"
    assert log.miktar == 2
    assert log.islem == "cikti"
    assign = db.query(models.StockAssignment).filter_by(donanim_tipi="ram").first()
    assert assign.miktar == 2


def test_stock_assign_updates_printer(db_session):
    db = db_session
    _setup_stock(db, "kartus")
    prn = models.Printer(ifs_no="IFS3")
    db.add(prn)
    db.commit()

    stock_assign(
        "kartus",
        1,
        "yazici",
        ifs_no="IFS3",
        hedef_envanter_no="INV200",
        sorumlu_personel="Mehmet",
        kullanim_alani="Depo",
        db=db,
    )

    prn = db.query(models.Printer).filter_by(ifs_no="IFS3").one()
    assert prn.sorumlu_personel == "Mehmet"
    assert prn.kullanim_alani == "Depo"
    assert prn.envanter_no == "INV200"
    log = db.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log.donanim_tipi == "kartus"
    assert log.miktar == 1
    assert log.islem == "cikti"
    assign = db.query(models.StockAssignment).filter_by(donanim_tipi="kartus").first()
    assert assign.hedef_envanter_no == "INV200"
