CREATE TABLE IF NOT EXISTS stock_logs (
  id INTEGER PRIMARY KEY,
  donanim_tipi TEXT NOT NULL,
  miktar INTEGER NOT NULL,
  ifs_no TEXT,
  marka TEXT,
  model TEXT,
  lisans_anahtari TEXT,
  mail_adresi TEXT,
  aciklama TEXT,
  tarih TEXT,
  islem TEXT NOT NULL,
  actor TEXT
);

CREATE TABLE IF NOT EXISTS stock_assignments (
  id INTEGER PRIMARY KEY,
  donanim_tipi TEXT NOT NULL,
  miktar INTEGER NOT NULL,
  ifs_no TEXT,
  hedef_envanter_no TEXT,
  sorumlu_personel TEXT,
  kullanim_alani TEXT,
  tarih TEXT,
  actor TEXT
);

