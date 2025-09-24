import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi import HTTPException

import models
from routes.admin import user_delete
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


def test_user_deletion_permissions(db_session):
    db = db_session
    admin = add_user(db, "admin", "admin")
    other_admin = add_user(db, "mod", "admin")
    normal = add_user(db, "alice", "user")

    normal_id = normal.id
    other_admin_id = other_admin.id

    user_delete(
        normal_id,
        user=SessionUser(other_admin_id, other_admin.username, other_admin.role),
        db=db,
    )
    assert db.get(models.User, normal_id) is None

    with pytest.raises(HTTPException):
        user_delete(
            admin.id,
            user=SessionUser(other_admin.id, other_admin.username, other_admin.role),
            db=db,
        )

    user_delete(
        other_admin_id, user=SessionUser(admin.id, admin.username, admin.role), db=db
    )
    assert db.get(models.User, other_admin_id) is None

    with pytest.raises(HTTPException):
        user_delete(
            admin.id, user=SessionUser(admin.id, admin.username, admin.role), db=db
        )
