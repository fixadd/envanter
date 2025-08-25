-- sql/seed_minimal.sql
INSERT OR IGNORE INTO brands (name) VALUES ('HP'), ('Canon');

INSERT OR IGNORE INTO models (brand_id, name)
SELECT b.id, 'LaserJet 1020' FROM brands b WHERE b.name='HP';
INSERT OR IGNORE INTO models (brand_id, name)
SELECT b.id, 'LBP631C' FROM brands b WHERE b.name='Canon';

INSERT OR IGNORE INTO factories (name) VALUES ('Merkez'), ('Organize Sanayi');
INSERT OR IGNORE INTO usage_areas (name) VALUES ('Muhasebe'), ('İK');
INSERT OR IGNORE INTO hardware_types (name) VALUES ('Yazıcı'), ('Bilgisayar');
INSERT OR IGNORE INTO license_names (name) VALUES ('Microsoft Office'), ('Windows Pro');

-- Kullanıcı (full_name dolu)
-- Parola hash'i olmadan demo; uygulama login akışında gerekecektir.
INSERT OR IGNORE INTO users (username, full_name, role, password_hash)
VALUES ('kadir','Kadir Can','user','demo'),
       ('mehmet','Mehmet Yılmaz','user','demo');
