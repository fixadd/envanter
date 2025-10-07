import asyncio
import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest

import models
from app.core.security import is_password_hash
from app.web.router import login_submit


class DummyRequest:
    def __init__(self):
        self.app = SimpleNamespace(state=SimpleNamespace())
        self.session: dict[str, object] = {}
        self.cookies: dict[str, str] = {}
        self.headers: dict[str, str] = {}


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def test_login_upgrades_plaintext_password(db_session):
    db = db_session
    user = models.User(
        username="demo", password_hash="demo", full_name="Demo Kullanıcı"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    request = DummyRequest()
    request.session["csrf_token"] = "token"

    response = asyncio.run(
        login_submit(
            request,
            username="demo",
            password="demo",
            remember=None,
            csrf_token="token",
            db=db,
        )
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert request.session["user_id"] == user.id

    db.refresh(user)
    assert user.password_hash != "demo"
    assert is_password_hash(user.password_hash)
