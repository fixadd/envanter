import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from datetime import datetime

import pytest

import models
from routers.stock import AssignPayload, stock_assign


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def _setup_stock(
    db,
    donanim_tipi,
    toplam=1,
    marka=None,
    model=None,
    ifs_no=None,
    lisans_anahtari=None,
    mail=None,
):
    db.add(models.StockTotal(donanim_tipi=donanim_tipi, toplam=toplam))
    db.add(
        models.StockLog(
            donanim_tipi=donanim_tipi,
            marka=marka,
            model=model,
            ifs_no=ifs_no,
            lisans_anahtari=lisans_anahtari,
            mail_adresi=mail,
            miktar=toplam,
            islem="girdi",
            tarih=datetime.utcnow(),
            actor="tester",
        )
    )
    db.commit()


def _make_user():
    return type("User", (), {"full_name": "Tester", "username": "tester"})()


def test_stock_assign_updates_license(db_session):
    db = db_session
    _setup_stock(
        db,
        "Ofis",
        toplam=1,
        ifs_no="IFS1",
        lisans_anahtari="KEY-123",
        mail="user@example.com",
    )

    payload = AssignPayload(
        stock_id="Ofis|||IFS1",
        atama_turu="lisans",
        miktar=1,
        license_form={
            "lisans_adi": "Office",
            "sorumlu_personel": "Ali",
            "bagli_envanter_no": "INV001",
            "mail_adresi": "destek@example.com",
        },
        notlar="Test notu",
    )

    stock_assign(payload, db=db, user=_make_user())

    lic = db.query(models.License).filter_by(bagli_envanter_no="INV001").one()
    assert lic.sorumlu_personel == "Ali"
    assert lic.mail_adresi == "destek@example.com"
    assert lic.lisans_anahtari == "KEY-123"
    assert lic.ifs_no == "IFS1"
    log = db.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log.donanim_tipi == "Ofis"
    assert log.miktar == 1
    assert log.ifs_no == "IFS1"
    assert log.islem == "cikti"
    assert log.aciklama == "Test notu"
    assign = db.query(models.StockAssignment).first()
    assert assign.hedef_envanter_no == "INV001"
    assert assign.sorumlu_personel == "Ali"


def test_stock_assign_updates_inventory(db_session):
    db = db_session
    _setup_stock(db, "Laptop", toplam=1, marka="Dell", model="Latitude")

    payload = AssignPayload(
        stock_id="Laptop|Dell|Latitude|",
        atama_turu="envanter",
        miktar=1,
        envanter_form={
            "envanter_no": "INV100",
            "bilgisayar_adi": "PC-100",
            "sorumlu_personel": "Veli",
            "kullanim_alani": "Ofis",
        },
        notlar="Ofis envanter",
    )

    stock_assign(payload, db=db, user=_make_user())

    inv = db.query(models.Inventory).filter_by(no="INV100").one()
    assert inv.ifs_no is None
    assert inv.sorumlu_personel == "Veli"
    assert inv.kullanim_alani == "Ofis"
    assert inv.marka == "Dell"
    assert inv.model == "Latitude"
    log = db.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log.donanim_tipi == "Laptop"
    assert log.miktar == 1
    assert log.islem == "cikti"
    assign = db.query(models.StockAssignment).filter_by(donanim_tipi="Laptop").first()
    assert assign.hedef_envanter_no == "INV100"


def test_stock_assign_updates_printer(db_session):
    db = db_session
    _setup_stock(db, "Kartus", toplam=1, marka="HP", model="1234", ifs_no="IFS3")

    payload = AssignPayload(
        stock_id="Kartus|HP|1234|IFS3",
        atama_turu="yazici",
        miktar=1,
        printer_form={
            "envanter_no": "INV200",
            "kullanim_alani": "Depo",
        },
    )

    stock_assign(payload, db=db, user=_make_user())

    prn = db.query(models.Printer).filter_by(envanter_no="INV200").one()
    assert prn.kullanim_alani == "Depo"
    assert prn.ifs_no == "IFS3"
    assert prn.marka == "HP"
    assert prn.model == "1234"
    log = db.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log.donanim_tipi == "Kartus"
    assert log.miktar == 1
    assert log.islem == "cikti"
    assign = db.query(models.StockAssignment).filter_by(donanim_tipi="Kartus").first()
    assert assign.hedef_envanter_no == "INV200"


def test_stock_assign_matches_lookup_display_values(db_session):
    db = db_session
    hw = models.HardwareType(name="Laptop")
    brand = models.Brand(name="Dell")
    db.add_all([hw, brand])
    db.commit()
    db.refresh(hw)
    db.refresh(brand)

    model = models.Model(name="Latitude", brand_id=brand.id)
    db.add(model)
    db.commit()
    db.refresh(model)

    _setup_stock(
        db,
        str(hw.id),
        toplam=2,
        marka=str(brand.id),
        model=str(model.id),
    )

    payload = AssignPayload(
        stock_id="Laptop|Dell|Latitude|",
        atama_turu="envanter",
        miktar=1,
        envanter_form={
            "envanter_no": "INV300",
            "bilgisayar_adi": "PC-300",
        },
    )

    stock_assign(payload, db=db, user=_make_user())

    inv = db.query(models.Inventory).filter_by(no="INV300").one()
    assert inv.donanim_tipi == "Laptop"
    assert inv.marka == "Dell"
    assert inv.model == "Latitude"

    log = db.query(models.StockLog).order_by(models.StockLog.id.desc()).first()
    assert log.donanim_tipi == str(hw.id)
    assert log.marka == str(brand.id)
    assert log.model == str(model.id)

    assign = (
        db.query(models.StockAssignment).filter_by(hedef_envanter_no="INV300").one()
    )
    assert assign.donanim_tipi == str(hw.id)
