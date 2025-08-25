# -*- coding: utf-8 -*-
import sqlite3, sys, os

DB_PATH = os.environ.get("ENV_DB_PATH", "/app/data/envanter.db")

REQUIRED_COLS = [
    ("lisans_adi", "TEXT"),
    ("lisans_anahtari", "TEXT"),
    ("sorumlu_personel", "TEXT"),
    ("bagli_envanter_no", "TEXT"),
    ("inventory_id", "INTEGER"),
    ("durum", "TEXT DEFAULT 'Aktif'"),
    ("notlar", "TEXT"),
]

def main():
    if not os.path.exists(DB_PATH):
        print(f"[X] DB bulunamadı: {DB_PATH}")
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(licenses);")
    existing = {row[1] for row in cur.fetchall()}  # kolon adları

    to_add = [c for c in REQUIRED_COLS if c[0] not in existing]
    if not to_add:
        print("[✓] licenses tablosu zaten güncel.")
        return

    for name, decl in to_add:
        sql = f"ALTER TABLE licenses ADD COLUMN {name} {decl};"
        print("[…] " + sql)
        cur.execute(sql)

    con.commit()
    con.close()
    print("[✓] Eksik kolon(lar) eklendi.")

if __name__ == "__main__":
    main()
