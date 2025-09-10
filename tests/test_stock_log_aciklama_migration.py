import sys
import sqlite3
import importlib
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_init_db_adds_aciklama_column(tmp_path, monkeypatch):
    db_file = tmp_path / "app.db"
    conn = sqlite3.connect(db_file)
    conn.execute(
        """
        CREATE TABLE stock_logs (
            id INTEGER PRIMARY KEY,
            donanim_tipi TEXT NOT NULL,
            miktar INTEGER NOT NULL,
            ifs_no TEXT,
            marka TEXT,
            model TEXT,
            lisans_anahtari TEXT,
            mail_adresi TEXT,
            tarih TEXT,
            islem TEXT NOT NULL,
            actor TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    sys.modules.pop("models", None)
    import models
    importlib.reload(models)

    models.init_db()

    from sqlalchemy import inspect

    insp = inspect(models.engine)
    cols = {c["name"] for c in insp.get_columns("stock_logs")}
    assert "aciklama" in cols

    db = models.SessionLocal()
    log = models.StockLog(donanim_tipi="mouse", miktar=1, islem="girdi", aciklama="test")
    db.add(log)
    db.commit()
    db.close()

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    sys.modules.pop("models", None)
    import models as _cleanup
    importlib.reload(_cleanup)
