import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi import HTTPException

import models
from routes.admin import create_user, user_edit_post
from security import SessionUser


@pytest.fixture()
def db_session():
    models.Base.metadata.create_all(models.engine)
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(models.engine)


def make_user(
    db,
    *,
    username: str,
    email: str | None = None,
    first_name: str = "",
    last_name: str = "",
    role: str = "user",
):
    user = models.User(
        username=username,
        password_hash="x",
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
    )
    user.full_name = f"{first_name} {last_name}".strip()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_user_rejects_duplicate_username(db_session):
    db = db_session
    make_user(db, username="alice")

    with pytest.raises(HTTPException) as exc:
        create_user(
            username=" alice ",
            password="secret",
            first_name="Alice",
            last_name="One",
            email="alice@example.com",
            db=db,
        )

    assert exc.value.status_code == 400
    assert "kullanıcı adı" in exc.value.detail.lower()


def test_create_user_rejects_duplicate_email(db_session):
    db = db_session
    make_user(db, username="bob", email="bob@example.com")

    with pytest.raises(HTTPException) as exc:
        create_user(
            username="bobby",
            password="secret",
            first_name="Bob",
            last_name="Builder",
            email=" bob@example.com ",
            db=db,
        )

    assert exc.value.status_code == 400
    assert "e-posta" in exc.value.detail.lower()


def test_edit_user_preserves_uniqueness(db_session):
    db = db_session
    admin = make_user(db, username="admin", role="admin")
    target = make_user(db, username="charlie", email="charlie@example.com")

    with pytest.raises(HTTPException) as exc:
        user_edit_post(
            target.id,
            username="admin",
            first_name="Charlie",
            last_name="Brown",
            email="charlie@example.com",
            password="",
            is_admin=False,
            user=SessionUser(admin.id, admin.username, admin.role),
            db=db,
        )

    assert exc.value.status_code == 400
    assert "kullanıcı adı" in exc.value.detail.lower()
