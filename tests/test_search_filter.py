import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
import models
from routers.api import users_list, inventory_list


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def test_users_list_search_and_role(db_session):
    db = db_session
    db.add_all([
        models.User(username="ali", password_hash="x", full_name="Ali Veli", role="user"),
        models.User(username="admin", password_hash="y", full_name="Admin User", role="admin"),
    ])
    db.commit()

    res = users_list(q="ali", db=db)
    assert len(res["items"]) == 1
    assert res["items"][0]["username"] == "ali"

    res2 = users_list(role="admin", db=db)
    assert len(res2["items"]) == 1
    assert res2["items"][0]["username"] == "admin"


def test_inventory_list_search_and_filters(db_session):
    db = db_session
    db.add_all([
        models.Inventory(
            no="INV1",
            fabrika="F1",
            departman="D1",
            sorumlu_personel="Ali",
            marka="HP",
            model="A",
            bilgisayar_adi="PC1",
            seri_no="S1",
            ifs_no="IFS1",
        ),
        models.Inventory(
            no="INV2",
            fabrika="F1",
            departman="D2",
            sorumlu_personel="Veli",
            marka="Dell",
            model="B",
            bilgisayar_adi="PC2",
            seri_no="S2",
            ifs_no="IFS2",
        ),
    ])
    db.commit()

    res = inventory_list(q="INV1", db=db)
    assert len(res["items"]) == 1
    assert res["items"][0]["no"] == "INV1"

    res2 = inventory_list(fabrika="F1", departman="D2", db=db)
    assert len(res2["items"]) == 1
    assert res2["items"][0]["no"] == "INV2"
