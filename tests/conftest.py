import os
import sys
from pathlib import Path
from types import SimpleNamespace

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest

import models


class DummyRequest:
    def __init__(self) -> None:
        state = SimpleNamespace(session_https_only=False)
        self.app = SimpleNamespace(state=state)
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


@pytest.fixture()
def dummy_request() -> DummyRequest:
    request = DummyRequest()
    request.session["csrf_token"] = "token"
    return request
