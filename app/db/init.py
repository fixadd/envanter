"""Database bootstrap and lightweight migration utilities."""

from __future__ import annotations

from sqlalchemy import inspect, text


def _table_exists(conn, name: str) -> bool:
    row = conn.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,)
    ).fetchone()
    return row is not None


def bootstrap_schema() -> None:
    """Perform ad-hoc schema adjustments for legacy SQLite databases."""

    from models import engine

    with engine.begin() as conn:
        if not _table_exists(conn, "licenses"):
            # Table does not exist yet; ORM ``create_all`` will create it later.
            return

        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info('licenses')")}
        stmts: list[str] = []

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
            stmts.append(
                "CREATE INDEX IF NOT EXISTS idx_licenses_inventory_id ON licenses(inventory_id);"
            )
        if "durum" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN durum TEXT DEFAULT 'aktif';")
        if "notlar" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN notlar TEXT;")
        if "license_code" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN license_code TEXT;")
            stmts.append(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_licenses_license_code ON licenses(license_code);"
            )
        if "license_type" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN license_type TEXT;")
        if "seat_count" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN seat_count INTEGER DEFAULT 1;")
        if "start_date" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN start_date DATE;")
        if "end_date" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN end_date DATE;")
        if "factory_id" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN factory_id INTEGER;")
        if "department_id" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN department_id INTEGER;")
        if "owner_id" not in cols:
            stmts.append("ALTER TABLE licenses ADD COLUMN owner_id INTEGER;")

        for stmt in stmts:
            conn.exec_driver_sql(stmt)

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


def init_db() -> None:
    """Create tables and perform lightweight migrations for SQLite."""

    from models import Base, engine

    # Create all tables if they do not exist
    Base.metadata.create_all(bind=engine)

    # Ensure recently introduced columns exist on older SQLite databases.
    # Missing fields trigger "no such column" errors when the ORM attempts to
    # access them. We inspect the schema and add or rename columns as needed.

    # -- Users ---------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("users")}
    with engine.begin() as conn:
        if "first_name" not in cols:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN first_name VARCHAR(60) DEFAULT ''")
            )
        if "last_name" not in cols:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN last_name VARCHAR(60) DEFAULT ''")
            )
        if "full_name" not in cols:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN full_name VARCHAR(120) DEFAULT ''")
            )
        if "email" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))
        if "role" not in cols:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(16) DEFAULT 'admin'")
            )
        if "theme" not in cols:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN theme VARCHAR(20) DEFAULT 'default'")
            )
        if "animation" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN animation VARCHAR(20) DEFAULT 'none'"
                )
            )
        if "created_at" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                )
            )

    # -- Lookups -------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("lookups")}
    with engine.begin() as conn:
        if "type" not in cols and "category" in cols:
            conn.execute(text("ALTER TABLE lookups RENAME COLUMN category TO type"))

    # -- Licenses --------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("licenses")}
    with engine.begin() as conn:
        if "license_code" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN license_code VARCHAR(64)"))
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_licenses_license_code ON licenses(license_code)"
                )
            )
        if "license_type" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN license_type VARCHAR(32)"))
        if "seat_count" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE licenses ADD COLUMN seat_count INTEGER DEFAULT 1"
                )
            )
        if "start_date" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN start_date DATE"))
        if "end_date" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN end_date DATE"))
        if "factory_id" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN factory_id INTEGER"))
        if "department_id" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN department_id INTEGER"))
        if "owner_id" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN owner_id INTEGER"))
        if "lisans_adi" not in cols:
            if "adi" in cols:
                conn.execute(
                    text("ALTER TABLE licenses RENAME COLUMN adi TO lisans_adi")
                )
            else:
                conn.execute(
                    text("ALTER TABLE licenses ADD COLUMN lisans_adi VARCHAR(200)")
                )
        if "lisans_anahtari" not in cols:
            if "anahtari" in cols:
                conn.execute(
                    text(
                        "ALTER TABLE licenses RENAME COLUMN anahtari TO lisans_anahtari"
                    )
                )
            else:
                conn.execute(
                    text("ALTER TABLE licenses ADD COLUMN lisans_anahtari VARCHAR(500)")
                )
        if "sorumlu_personel" not in cols:
            conn.execute(
                text("ALTER TABLE licenses ADD COLUMN sorumlu_personel VARCHAR(150)")
            )
        if "bagli_envanter_no" not in cols:
            conn.execute(
                text("ALTER TABLE licenses ADD COLUMN bagli_envanter_no VARCHAR(150)")
            )
        if "inventory_id" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN inventory_id INTEGER"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_licenses_inventory_id ON licenses(inventory_id)"
                )
            )
        if "durum" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE licenses ADD COLUMN durum VARCHAR(20) DEFAULT 'aktif'"
                )
            )
        if "notlar" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN notlar TEXT"))
        if "ifs_no" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN ifs_no VARCHAR(100)"))
        if "tarih" not in cols:
            conn.execute(text("ALTER TABLE licenses ADD COLUMN tarih DATE"))
        if "islem_yapan" not in cols:
            conn.execute(
                text("ALTER TABLE licenses ADD COLUMN islem_yapan VARCHAR(120)")
            )
        if "mail_adresi" not in cols:
            conn.execute(
                text("ALTER TABLE licenses ADD COLUMN mail_adresi VARCHAR(200)")
            )
        if "departments" not in insp.get_table_names():
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS departments ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                    "name VARCHAR(150) NOT NULL UNIQUE"
                    ")"
                )
            )

    # -- License Logs ----------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("license_logs")}
    with engine.begin() as conn:
        if "islem" not in cols:
            if "field" in cols:
                conn.execute(
                    text("ALTER TABLE license_logs RENAME COLUMN field TO islem")
                )
            else:
                conn.execute(
                    text("ALTER TABLE license_logs ADD COLUMN islem VARCHAR(50)")
                )
        if "detay" not in cols:
            if "old_value" in cols:
                conn.execute(
                    text("ALTER TABLE license_logs RENAME COLUMN old_value TO detay")
                )
            else:
                conn.execute(text("ALTER TABLE license_logs ADD COLUMN detay TEXT"))
        if "islem_yapan" not in cols:
            if "changed_by" in cols:
                conn.execute(
                    text(
                        "ALTER TABLE license_logs RENAME COLUMN changed_by TO islem_yapan"
                    )
                )
            else:
                conn.execute(
                    text("ALTER TABLE license_logs ADD COLUMN islem_yapan VARCHAR(120)")
                )
        if "tarih" not in cols:
            if "changed_at" in cols:
                conn.execute(
                    text("ALTER TABLE license_logs RENAME COLUMN changed_at TO tarih")
                )
            else:
                conn.execute(text("ALTER TABLE license_logs ADD COLUMN tarih DATETIME"))

    # -- Inventories -----------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("inventories")}
    with engine.begin() as conn:
        if "bagli_envanter_no" not in cols:
            if "bagli_makina_no" in cols:
                conn.execute(
                    text(
                        "ALTER TABLE inventories RENAME COLUMN bagli_makina_no TO bagli_envanter_no"
                    )
                )
            else:
                conn.execute(
                    text(
                        "ALTER TABLE inventories ADD COLUMN bagli_envanter_no VARCHAR(150)"
                    )
                )
        if "kullanim_alani" not in cols:
            conn.execute(
                text("ALTER TABLE inventories ADD COLUMN kullanim_alani VARCHAR(150)")
            )
        if "durum" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE inventories ADD COLUMN durum VARCHAR(50) DEFAULT 'aktif'"
                )
            )
        if "ifs_no" not in cols:
            conn.execute(text("ALTER TABLE inventories ADD COLUMN ifs_no VARCHAR(150)"))

    # -- Talepler --------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("talepler")}
    with engine.begin() as conn:
        if "donanim_tipi" not in cols:
            conn.execute(
                text("ALTER TABLE talepler ADD COLUMN donanim_tipi VARCHAR(150)")
            )
        if "kapanma_tarihi" not in cols:
            conn.execute(
                text("ALTER TABLE talepler ADD COLUMN kapanma_tarihi DATETIME")
            )
        if "karsilanan_miktar" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE talepler ADD COLUMN karsilanan_miktar INTEGER DEFAULT 0"
                )
            )
        if "kalan_miktar" not in cols:
            conn.execute(
                text("ALTER TABLE talepler ADD COLUMN kalan_miktar INTEGER DEFAULT 0")
            )

    # -- Printers --------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("printers")}
    with engine.begin() as conn:
        if "inventory_id" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN inventory_id INTEGER"))
        if "marka" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN marka VARCHAR(100)"))
        if "model" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN model VARCHAR(100)"))
        if "seri_no" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN seri_no VARCHAR(100)"))
        if "fabrika" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN fabrika VARCHAR(100)"))
        if "kullanim_alani" not in cols:
            conn.execute(
                text("ALTER TABLE printers ADD COLUMN kullanim_alani VARCHAR(150)")
            )
        if "sorumlu_personel" not in cols:
            conn.execute(
                text("ALTER TABLE printers ADD COLUMN sorumlu_personel VARCHAR(150)")
            )
        if "bagli_envanter_no" not in cols:
            conn.execute(
                text("ALTER TABLE printers ADD COLUMN bagli_envanter_no VARCHAR(50)")
            )
        if "durum" not in cols:
            conn.execute(
                text(
                    "ALTER TABLE printers ADD COLUMN durum VARCHAR(30) DEFAULT 'aktif'"
                )
            )
        if "notlar" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN notlar TEXT"))
        if "envanter_no" not in cols:
            conn.execute(
                text("ALTER TABLE printers ADD COLUMN envanter_no VARCHAR(100)")
            )
        if "ip_adresi" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN ip_adresi VARCHAR(50)"))
        if "mac" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN mac VARCHAR(50)"))
        if "hostname" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN hostname VARCHAR(100)"))
        if "ifs_no" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN ifs_no VARCHAR(100)"))
        if "tarih" not in cols:
            conn.execute(text("ALTER TABLE printers ADD COLUMN tarih DATE"))
        if "islem_yapan" not in cols:
            conn.execute(
                text("ALTER TABLE printers ADD COLUMN islem_yapan VARCHAR(150)")
            )

    # -- Stock Logs --------------------------------------------------------------
    insp = inspect(engine)
    cols = {col["name"] for col in insp.get_columns("stock_logs")}
    with engine.begin() as conn:
        if "ifs_no" not in cols:
            conn.execute(text("ALTER TABLE stock_logs ADD COLUMN ifs_no VARCHAR(100)"))
        if "marka" not in cols:
            conn.execute(text("ALTER TABLE stock_logs ADD COLUMN marka VARCHAR(150)"))
        if "model" not in cols:
            conn.execute(text("ALTER TABLE stock_logs ADD COLUMN model VARCHAR(150)"))
        if "lisans_anahtari" not in cols:
            conn.execute(
                text("ALTER TABLE stock_logs ADD COLUMN lisans_anahtari VARCHAR(500)")
            )
        if "mail_adresi" not in cols:
            conn.execute(
                text("ALTER TABLE stock_logs ADD COLUMN mail_adresi VARCHAR(200)")
            )
        if "aciklama" not in cols:
            conn.execute(text("ALTER TABLE stock_logs ADD COLUMN aciklama TEXT"))
        if "actor" not in cols:
            conn.execute(text("ALTER TABLE stock_logs ADD COLUMN actor VARCHAR(150)"))
        if "source_type" not in cols:
            conn.execute(
                text("ALTER TABLE stock_logs ADD COLUMN source_type VARCHAR(50)")
            )
        if "source_id" not in cols:
            conn.execute(text("ALTER TABLE stock_logs ADD COLUMN source_id INTEGER"))
