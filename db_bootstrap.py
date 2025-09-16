from models import engine


def _table_exists(conn, name: str) -> bool:
    row = conn.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,)
    ).fetchone()
    return row is not None


def bootstrap_schema():
    with engine.begin() as conn:
        if not _table_exists(conn, "licenses"):
            return  # tablo yoksa dokunma (ORM create_all başka yerde çalışıyor demektir)

        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info('licenses')")}
        stmts = []

        if "sorumlu_personel" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN sorumlu_personel TEXT;")
        if "ifs_no" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN ifs_no TEXT;")
        if "tarih" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN tarih DATE;")
        if "islem_yapan" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN islem_yapan TEXT;")
        if "mail_adresi" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN mail_adresi TEXT;")
        if "inventory_id" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN inventory_id INTEGER;")
            stmts.append("CREATE INDEX IF NOT EXISTS idx_licenses_inventory_id ON licenses(inventory_id);")
        if "durum" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN durum TEXT DEFAULT 'aktif';")
        if "notlar" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN notlar TEXT;")

        for s in stmts:
            conn.exec_driver_sql(s)

        # Log tablosu
        conn.exec_driver_sql(
            """
        CREATE TABLE IF NOT EXISTS license_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          license_id INTEGER NOT NULL,
          field TEXT NOT NULL,
          old_value TEXT,
          new_value TEXT,
          changed_by TEXT,
          changed_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY(license_id) REFERENCES licenses(id) ON DELETE CASCADE
        );
        """
        )
