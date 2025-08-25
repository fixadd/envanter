-- Gerekli yeni sütunlar (yoksa eklerken hata vermez; SQLite ekler)
ALTER TABLE licenses ADD COLUMN sorumlu_personel TEXT;
ALTER TABLE licenses ADD COLUMN ifs_no TEXT;
ALTER TABLE licenses ADD COLUMN tarih DATE;
ALTER TABLE licenses ADD COLUMN islem_yapan TEXT;
ALTER TABLE licenses ADD COLUMN mail_adresi TEXT;

-- Envanter bağı (yoksa aç)
ALTER TABLE licenses ADD COLUMN inventory_id INTEGER REFERENCES inventories(id) ON DELETE SET NULL;

-- İndeks
CREATE INDEX IF NOT EXISTS idx_licenses_inventory_id ON licenses(inventory_id);

-- Log tablosu
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
