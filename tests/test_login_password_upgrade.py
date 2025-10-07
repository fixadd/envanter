import asyncio

import models
from passlib.context import CryptContext

from app.core.security import is_password_hash, pwd_context
from app.web.router import login_submit


def test_login_upgrades_plaintext_password(db_session, dummy_request):
    db = db_session
    user = models.User(
        username="demo", password_hash="demo", full_name="Demo Kullanıcı"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    request = dummy_request

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


def test_login_upgrades_legacy_hash(db_session, dummy_request):
    db = db_session
    legacy_context = CryptContext(schemes=["pbkdf2_sha256"])
    legacy_hash = legacy_context.hash("demo")
    user = models.User(
        username="demo", password_hash=legacy_hash, full_name="Demo Kullanıcı"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    request = dummy_request

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
    assert is_password_hash(user.password_hash)
    assert pwd_context.identify(user.password_hash) == "bcrypt"
