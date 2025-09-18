from concurrent.futures import ThreadPoolExecutor
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(str(Path(__file__).resolve().parents[1]))

import models
from routers.stock import stock_assign, AssignPayload
from fastapi import HTTPException


def _setup_engine():
    database_url = "sqlite://"
    engine = create_engine(
        database_url,
        poolclass=StaticPool,
        **models.engine_kwargs_for_url(database_url),
    )
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    models.Base.metadata.create_all(engine)
    return engine, TestingSession


def test_concurrent_assignments():
    engine, SessionLocal = _setup_engine()

    with SessionLocal() as db:
        db.add(models.StockTotal(donanim_tipi="cpu", toplam=1))
        db.add(
            models.StockLog(
                donanim_tipi="cpu",
                miktar=1,
                islem="girdi",
                tarih=datetime.utcnow(),
                actor="test",
            )
        )
        db.commit()

    payload_kwargs = {
        "stock_id": "cpu|||",
        "atama_turu": "envanter",
        "miktar": 1,
        "envanter_form": {
            "envanter_no": "INV-TEST",
            "bilgisayar_adi": "PC-TEST",
        },
    }

    def worker():
        session = SessionLocal()
        try:
            stock_assign(AssignPayload(**payload_kwargs), db=session)
            return True
        except HTTPException:
            session.rollback()
            return False
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as exc:
        future1 = exc.submit(worker)
        result1 = future1.result()
        # ikinci atamayı neredeyse aynı anda başlatıyoruz ancak
        # ilk işlemin sonucunu aldıktan sonra gönderiyoruz.
        future2 = exc.submit(worker)
        result2 = future2.result()
        results = [result1, result2]

    assert results.count(True) == 1
    assert results.count(False) == 1

    with SessionLocal() as db:
        total = db.get(models.StockTotal, "cpu")
        assert total.toplam == 0
        # one giriş, one çıkış logu olmalı
        assert db.query(models.StockLog).count() == 2

