import os
import importlib

from sqlalchemy import inspect


def test_init_db_adds_new_columns(tmp_path):
    db_file = tmp_path / "talepler.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    import models
    importlib.reload(models)

    with models.engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE talepler (
                id INTEGER PRIMARY KEY,
                tur VARCHAR(50)
            )
            """
        )

    models.init_db()

    insp = inspect(models.engine)
    cols = {c["name"] for c in insp.get_columns("talepler")}
    assert "kapanma_tarihi" in cols
    assert "karsilanan_miktar" in cols
    assert "kalan_miktar" in cols

    models.engine.dispose()
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    importlib.reload(models)
