import asyncio

import models
from app.core.security import hash_password
from app.web.router import login_submit


def test_login_accepts_case_insensitive_username(db_session, dummy_request):
    db = db_session
    user = models.User(
        username="demo",
        password_hash=hash_password("demo"),
        full_name="Demo Kullanıcı",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    request = dummy_request

    response = asyncio.run(
        login_submit(
            request,
            username="DeMo",
            password="demo",
            remember="1",
            csrf_token="token",
            db=db,
        )
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert request.session["user_id"] == user.id
    assert request.session["user_name"] == user.full_name
    assert request.session["user_role"] == user.role
    assert "saved_username=demo" in response.headers.get("set-cookie", "")
