import os
import sys
from pathlib import Path

from sqlalchemy import inspect

sys.path.append(str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models  # noqa: E402


def test_stock_transactions_model_removed():
    models.Base.metadata.create_all(models.engine)
    try:
        inspector = inspect(models.engine)
        assert "stock_transactions" not in inspector.get_table_names()
        assert not hasattr(models, "StockTransaction")
    finally:
        models.Base.metadata.drop_all(models.engine)
