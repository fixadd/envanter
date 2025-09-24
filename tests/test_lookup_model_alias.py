import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models
from routers.lookup import lookup_model


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def _seed(db):
    b = models.Brand(name="Asus")
    db.add(b)
    db.flush()
    db.add(models.Model(name="A1", brand_id=b.id))
    db.commit()
    return b


def test_lookup_model_alias_with_name(db_session):
    b = _seed(db_session)
    res = lookup_model(marka=b.name, db=db_session)
    assert res and res[0]["name"] == "A1"


def test_lookup_model_alias_with_id(db_session):
    b = _seed(db_session)
    res = lookup_model(marka=str(b.id), db=db_session)
    assert res and res[0]["name"] == "A1"


def test_lookup_model_requires_brand(db_session):
    _seed(db_session)
    with pytest.raises(HTTPException):
        lookup_model(marka_id=None, marka=None, db=db_session)
