import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi import HTTPException

import models
from routes.admin import user_edit_post
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


def add_user(db, username, role="user"):
    u = models.User(username=username, password_hash="x", role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def edit_user(
    uid,
    acting_user,
    db,
    username=None,
    first_name="",
    last_name="",
    email="",
    password="",
    is_admin=None,
):
    target = db.get(models.User, uid)
    return user_edit_post(
        uid,
        username=username or target.username,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        is_admin=is_admin if is_admin is not None else target.role == "admin",
        user=SessionUser(acting_user.id, acting_user.username, acting_user.role),
        db=db,
    )


def test_admin_edit_permissions(db_session):
    db = db_session
    admin = add_user(db, "admin", "admin")
    other_admin = add_user(db, "mod", "admin")
    third_admin = add_user(db, "ops", "admin")
    normal_user = add_user(db, "alice", "user")

    # Admin can edit normal users
    edit_user(normal_user.id, admin, db, first_name="Alice")
    updated = db.get(models.User, normal_user.id)
    assert updated.first_name == "Alice"

    # Other admins cannot edit the primary admin
    with pytest.raises(HTTPException):
        edit_user(admin.id, other_admin, db, first_name="Root")

    # Other admins cannot edit each other
    with pytest.raises(HTTPException):
        edit_user(third_admin.id, other_admin, db, first_name="Ops")

    # Admin user can edit all other admins
    edit_user(third_admin.id, admin, db, first_name="Operations")
    refreshed = db.get(models.User, third_admin.id)
    assert refreshed.first_name == "Operations"

    # Admins can edit themselves
    edit_user(other_admin.id, other_admin, db, first_name="Moderator")
    assert db.get(models.User, other_admin.id).first_name == "Moderator"
