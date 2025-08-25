-- printer ekstra kolonlar
ALTER TABLE printers ADD COLUMN fabrika TEXT;
ALTER TABLE printers ADD COLUMN kullanim_alani TEXT;
ALTER TABLE printers ADD COLUMN sorumlu_personel TEXT;
ALTER TABLE printers ADD COLUMN bagli_envanter_no TEXT;
ALTER TABLE printers ADD COLUMN durum TEXT DEFAULT 'aktif';
ALTER TABLE printers ADD COLUMN notlar TEXT;

-- tarihçe
CREATE TABLE IF NOT EXISTS printer_histories (
  id INTEGER PRIMARY KEY,
  printer_id INTEGER,
  action TEXT,
  changes TEXT,
  actor TEXT,
  created_at TEXT
);

-- hurdalar (opsiyonel)
CREATE TABLE IF NOT EXISTS scrap_printers (
  id INTEGER PRIMARY KEY,
  printer_id INTEGER UNIQUE,
  snapshot TEXT,
  reason TEXT,
  created_at TEXT
);

