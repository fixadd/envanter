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

INSERT OR IGNORE INTO users (username, full_name, role, password_hash)
VALUES (
    'kadir',
    'Kadir Can',
    'user',
    '$2b$12$xRqrD1QKrHmAiwIMFHfDiOD.FuHln0R5BK3fbYf9Qb.V./dbM/Lmu'
),
(
    'mehmet',
    'Mehmet Yılmaz',
    'user',
    '$2b$12$rFExvANzbhJx6rATYpnDreL1ZeF5LfToIeS70QLle3XZGxJuFJOfC'
);
