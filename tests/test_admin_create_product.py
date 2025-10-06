import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from urllib.parse import urlencode

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import inspect

import models
from database import get_db
from routes.admin import router as admin_router


def _call_app(
    app: FastAPI, method: str, path: str, data: dict[str, str]
) -> tuple[int, dict[bytes, bytes], bytes]:
    body = urlencode(data or {}).encode()

    async def _request() -> tuple[int, dict[bytes, bytes], bytes]:
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method.upper(),
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [
                (b"host", b"testserver"),
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"content-length", str(len(body)).encode()),
            ],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "scheme": "http",
        }

        response_status = 500
        response_headers: dict[bytes, bytes] = {}
        response_body = bytearray()
        sent = False

        async def receive():
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }

        async def send(message):
            nonlocal response_status, response_headers, response_body
            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = dict(message.get("headers", []))
            elif message["type"] == "http.response.body":
                response_body.extend(message.get("body", b""))

        await app(scope, receive, send)
        return response_status, response_headers, bytes(response_body)

    return anyio.run(_request)


@pytest.fixture()
def client():
    models.Base.metadata.drop_all(models.engine)
    models.Base.metadata.create_all(models.engine)
    models.Product.__table__.drop(models.engine, checkfirst=True)
    assert not inspect(models.engine).has_table("products")

    app = FastAPI()
    app.include_router(admin_router)

    def override_get_db():
        db = models.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield lambda method, path, data=None: _call_app(app, method, path, data or {})
    finally:
        app.dependency_overrides.clear()
        models.Base.metadata.drop_all(models.engine)


def test_create_product_without_products_table(client):
    status_code, headers, _ = client(
        "POST",
        "/admin/products/create",
        data={
            "donanim_tipi": "   Laptop   ",
            "marka": "Dell",
            "model": "XPS 15",
            "kullanim_alani": "Ofis",
            "lisans_adi": "Windows 11",
            "fabrika": "Merkez",
        },
    )

    assert status_code == 303
    assert headers.get(b"location") == b"/admin#products"

    inspector = inspect(models.engine)
    assert inspector.has_table("products")

    with models.SessionLocal() as session:
        products = session.query(models.Product).all()

    assert len(products) == 1
    stored = products[0]
    assert stored.donanim_tipi == "Laptop"
    assert stored.marka == "Dell"
    assert stored.model == "XPS 15"
    assert stored.kullanim_alani == "Ofis"
    assert stored.lisans_adi == "Windows 11"
    assert stored.fabrika == "Merkez"
