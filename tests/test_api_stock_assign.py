import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models  # noqa: E402
from routers.api import stock_assign  # noqa: E402


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def test_stock_assign_succeeds_with_direct_queries(db_session):
    db = db_session
    db.add(models.StockTotal(donanim_tipi="Laptop", toplam=5))
    db.add(
        models.StockLog(
            donanim_tipi="Laptop",
            miktar=5,
            islem="girdi",
            ifs_no="IFS-1",
            tarih=datetime.now(UTC),
        )
    )
    db.add(models.Inventory(no="INV-1", donanim_tipi="Laptop"))
    db.commit()

    result = stock_assign(
        donanim_tipi="Laptop",
        miktar=3,
        hedef_tur="envanter",
        ifs_no="IFS-1",
        hedef_envanter_no="INV-1",
        db=db,
    )

    assert result["ok"] is True
    total = db.get(models.StockTotal, "Laptop")
    assert total.toplam == 2
    inventory = db.query(models.Inventory).filter_by(no="INV-1").one()
    assert inventory.ifs_no == "IFS-1"


def test_stock_assign_raises_on_insufficient_stock(db_session):
    db = db_session
    db.add(models.StockTotal(donanim_tipi="Monitor", toplam=1))
    db.add(
        models.StockLog(
            donanim_tipi="Monitor",
            miktar=1,
            islem="girdi",
            ifs_no="IFS-2",
            tarih=datetime.now(UTC),
        )
    )
    db.add(models.Inventory(no="INV-2", donanim_tipi="Monitor"))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        stock_assign(
            donanim_tipi="Monitor",
            miktar=2,
            hedef_tur="envanter",
            ifs_no="IFS-2",
            hedef_envanter_no="INV-2",
            db=db,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Yetersiz stok"


def test_stock_assign_requires_ifs_when_multiple_candidates(db_session):
    db = db_session
    db.add(models.StockTotal(donanim_tipi="Tablet", toplam=4))
    db.add(
        models.StockLog(
            donanim_tipi="Tablet",
            miktar=2,
            islem="girdi",
            ifs_no="IFS-A",
            tarih=datetime.now(UTC),
        )
    )
    db.add(
        models.StockLog(
            donanim_tipi="Tablet",
            miktar=2,
            islem="girdi",
            ifs_no="IFS-B",
            tarih=datetime.now(UTC),
        )
    )
    db.add(models.Inventory(no="INV-3", donanim_tipi="Tablet"))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        stock_assign(
            donanim_tipi="Tablet",
            miktar=1,
            hedef_tur="envanter",
            hedef_envanter_no="INV-3",
            db=db,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Birden fazla IFS bulundu, seçim gerekli"
