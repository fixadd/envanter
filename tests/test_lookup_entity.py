import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest

import models
from routers.api import lookup_entity


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def test_lookup_donanim_tipi(db_session):
    db = db_session
    db.add_all(
        [
            models.HardwareType(name="B"),
            models.HardwareType(name="A"),
        ]
    )
    db.commit()

    res = lookup_entity("donanim_tipi", db=db)
    assert res == ["A", "B"]


def test_lookup_marka_model(db_session):
    db = db_session
    brand = models.Brand(name="Dell")
    model = models.Model(name="XPS", brand=brand)
    db.add_all([brand, model])
    db.commit()

    assert lookup_entity("marka", db=db) == ["Dell"]
    assert lookup_entity("model", db=db) == ["XPS"]
