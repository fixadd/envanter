from sqlalchemy.orm import Session

from models import Brand, Model, Printer, SessionLocal

db: Session = SessionLocal()

# 1) Markaları oluştur
markalar = {
    p.yazici_markasi.strip(): None for p in db.query(Printer).all() if p.yazici_markasi
}
for name in sorted(m for m in markalar if m):
    b = db.query(Brand).filter(Brand.name.ilike(name)).first()
    if not b:
        b = Brand(name=name)
        db.add(b)
        db.commit()
    markalar[name] = b.id

# 2) Modelleri oluştur
for p in db.query(Printer).all():
    if not p.yazici_markasi or not p.yazici_modeli:
        continue
    bid = markalar.get(p.yazici_markasi.strip())
    if not bid:
        continue
    m = (
        db.query(Model)
        .filter(Model.brand_id == bid, Model.name.ilike(p.yazici_modeli.strip()))
        .first()
    )
    if not m:
        m = Model(brand_id=bid, name=p.yazici_modeli.strip())
        db.add(m)
        db.commit()

# 3) Yazıcılara brand_id/model_id bağla
for p in db.query(Printer).all():
    bname = (p.yazici_markasi or "").strip()
    mname = (p.yazici_modeli or "").strip()
    if not bname or not mname:
        continue
    b = db.query(Brand).filter(Brand.name.ilike(bname)).first()
    m = (
        db.query(Model).filter(Model.brand_id == b.id, Model.name.ilike(mname)).first()
        if b
        else None
    )
    if b and m:
        p.brand_id = b.id
        p.model_id = m.id

db.commit()
db.close()
