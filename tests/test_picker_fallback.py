import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest

import models
from routers.picker import picker_list


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def test_picker_list_uses_lookup_table_when_primary_empty(db_session):
    db = db_session
    db.add(models.Lookup(type="donanim_tipi", value="Monitör"))
    db.commit()
    req = SimpleNamespace(query_params={})
    res = picker_list("donanim_tipi", request=req, db=db)
    assert res == [{"id": 1, "text": "Monitör"}]
