import os
import sys
import importlib
from pathlib import Path

import pytest
from sqlalchemy import inspect

sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_init_db_adds_theme_and_animation_columns(tmp_path):
    db_file = tmp_path / "theme.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    import models
    importlib.reload(models)

    with models.engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY, 
                username VARCHAR(64) UNIQUE,
                password_hash VARCHAR(255),
                first_name VARCHAR(60) DEFAULT '',
                last_name VARCHAR(60) DEFAULT '',
                full_name VARCHAR(120) DEFAULT '',
                email VARCHAR(255),
                role VARCHAR(16) DEFAULT 'admin',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    models.init_db()

    insp = inspect(models.engine)
    cols = {c["name"] for c in insp.get_columns("users")}
    assert "theme" in cols
    assert "animation" in cols

    # restore default in-memory database for subsequent tests
    models.engine.dispose()
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    importlib.reload(models)
