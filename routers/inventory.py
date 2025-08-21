from fastapi import APIRouter, Depends, Request, HTTPException, Form
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models import Inventory, InventoryLog
from auth import get_db
from .inventory_schemas import InventoryCreate, InventoryUpdate

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_class=HTMLResponse)
def inventory_list(request: Request, db: Session = Depends(get_db)):
    rows = db.query(
        Inventory.id,
        Inventory.no,
        Inventory.fabrika,
        Inventory.departman,
        Inventory.donanim_tipi,
        Inventory.bilgisayar_adi,
        Inventory.sorumlu_personel,
    ).order_by(Inventory.id.desc()).all()

    return templates.TemplateResponse(
        "inventory_list.html", {"request": request, "rows": rows}
    )


@router.get("/{no}", response_class=HTMLResponse)
def inventory_detail(no: str, request: Request, db: Session = Depends(get_db)):
    inv = db.query(Inventory).filter(Inventory.no == no).first()
    if not inv:
        raise HTTPException(404, "Kayıt bulunamadı")

    logs = (
        db.query(InventoryLog)
        .filter(InventoryLog.inventory_id == inv.id)
        .order_by(InventoryLog.changed_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "inventory_detail.html", {"request": request, "item": inv, "logs": logs}
    )


@router.post("", response_model=None)
def create_inventory(payload: InventoryCreate, db: Session = Depends(get_db)):
    exists = db.query(Inventory).filter(Inventory.no == payload.no).first()
    if exists:
        raise HTTPException(400, "Aynı envanter no var")
    inv = Inventory(**payload.model_dump())
    db.add(inv)
    db.commit()
    return {"ok": True}


@router.post("/{no}/update", response_model=None)
def update_inventory(no: str, payload: InventoryUpdate, db: Session = Depends(get_db)):
    inv = db.query(Inventory).filter(Inventory.no == no).first()
    if not inv:
        raise HTTPException(404, "Kayıt yok")

    mutable_fields = [
        "fabrika",
        "departman",
        "donanim_tipi",
        "bilgisayar_adi",
        "marka",
        "model",
        "seri_no",
        "sorumlu_personel",
        "bagli_makina_no",
        "ifs_no",
        "tarih",
        "islem_yapan",
        "notlar",
    ]

    changer = payload.islem_yapan or "Sistem"

    for f in mutable_fields:
        new_val = getattr(payload, f, None)
        if new_val is None:
            continue
        old_val = getattr(inv, f)
        if new_val != old_val:
            setattr(inv, f, new_val)
            db.add(
                InventoryLog(
                    inventory_id=inv.id,
                    field=f,
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val) if new_val is not None else None,
                    changed_by=changer,
                )
            )
    db.commit()
    return {"ok": True}


@router.get("/add", response_class=HTMLResponse)
def inventory_add_form(request: Request):
    return templates.TemplateResponse("inventory_add.html", {"request": request})


@router.post("/add", response_class=HTMLResponse)
def inventory_add(
    no: str = Form(...),
    fabrika: str | None = Form(None),
    departman: str | None = Form(None),
    donanim_tipi: str | None = Form(None),
    bilgisayar_adi: str | None = Form(None),
    sorumlu_personel: str | None = Form(None),
    db: Session = Depends(get_db),
):
    payload = InventoryCreate(
        no=no,
        fabrika=fabrika,
        departman=departman,
        donanim_tipi=donanim_tipi,
        bilgisayar_adi=bilgisayar_adi,
        sorumlu_personel=sorumlu_personel,
    )
    exists = db.query(Inventory).filter(Inventory.no == payload.no).first()
    if exists:
        raise HTTPException(400, "Aynı envanter no var")
    inv = Inventory(**payload.model_dump())
    db.add(inv)
    db.commit()
    return RedirectResponse("/inventory", status_code=303)

