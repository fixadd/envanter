import models
from app.core.security import verify_password
from scripts.reset_admin_password import reset_password


def make_user(db, username: str, password_hash: str = "x", full_name: str = "Test"):
    user = models.User(
        username=username,
        password_hash=password_hash,
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_reset_password_updates_hash(db_session):
    db = db_session
    user = make_user(db, "admin", "old", "Admin")

    assert reset_password("admin", "yeniParola123", db=db)

    db.refresh(user)
    assert verify_password("yeniParola123", user.password_hash)


def test_reset_password_case_insensitive_lookup(db_session):
    db = db_session
    user = make_user(db, "destek", "old", "Destek")

    assert reset_password("DeStEk", "guncel123", db=db)

    db.refresh(user)
    assert verify_password("guncel123", user.password_hash)


def test_reset_password_returns_false_when_user_missing(db_session):
    db = db_session
    assert not reset_password("bilinmeyen", "deneme123", db=db)
