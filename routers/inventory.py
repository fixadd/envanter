from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import Factory, Inventory, InventoryLog, ScrapItem, User
from security import current_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", name="inventory.list")
def list_items(
    request: Request, db: Session = Depends(get_db), user=Depends(current_user)
):
    items = (
        db.query(Inventory)
        .filter(Inventory.durum != "hurda")
        .order_by(Inventory.id.desc())
        .all()
    )
    return templates.TemplateResponse(
        "inventory_list.html", {"request": request, "items": items}
    )


@router.get("/new", name="inventory.new")
def new_page(request: Request, user=Depends(current_user)):
    return templates.TemplateResponse("inventory_add.html", {"request": request})


@router.post("/new", name="inventory.new_post")
async def new_post(
    request: Request, db: Session = Depends(get_db), user=Depends(current_user)
):
    form = dict(await request.form())
    inv = Inventory(
        no=form.get("no") or f"INV{int(datetime.utcnow().timestamp())}",
        fabrika=form.get("fabrika"),
        departman=form.get("departman"),
        donanim_tipi=form.get("donanim_tipi"),
        bilgisayar_adi=form.get("bilgisayar_adi"),
        marka=form.get("marka"),
        model=form.get("model"),
        seri_no=form.get("seri_no"),
        ifs_no=form.get("ifs_no"),
        not_=form.get("not") or None,
        tarih=datetime.utcnow(),
        islem_yapan=getattr(user, "full_name", None) or user.username,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    db.add(
        InventoryLog(
            inventory_id=inv.id,
            action="create",
            before_json=None,
            after_json=inv.to_dict() if hasattr(inv, "to_dict") else None,
            note="Oluşturuldu",
            created_at=datetime.utcnow(),
            actor=user.username,
        )
    )
    db.commit()
    return RedirectResponse(
        url=request.url_for("inventory.detail", item_id=inv.id), status_code=303
    )


@router.get("/{item_id}/detail", name="inventory.detail")
def detail(
    request: Request,
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    stmt = (
        select(Inventory)
        .options(selectinload(Inventory.licenses))
        .where(Inventory.id == item_id)
    )
    item = db.execute(stmt).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
    logs = (
        db.query(InventoryLog)
        .filter(InventoryLog.inventory_id == item_id)
        .order_by(InventoryLog.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "inventory_detail.html", {"request": request, "inv": item, "logs": logs}
    )


@router.get("/assign/sources", name="inventory.assign_sources")
def assign_sources(
    type: str, exclude_id: int | None = None, db: Session = Depends(get_db)
):
    if type == "users":
        users = db.query(User).order_by(User.full_name.asc()).all()
        return [
            {"id": u.full_name or u.username, "text": u.full_name or u.username}
            for u in users
            if (u.full_name or u.username or "").strip()
        ]
    if type == "fabrika":
        rows = db.query(Factory).order_by(Factory.name.asc()).all()
        return [{"id": r.name, "text": r.name} for r in rows]
    if type == "departman":
        rows = (
            db.query(Inventory.departman)
            .filter(Inventory.departman.isnot(None))
            .distinct()
            .order_by(Inventory.departman.asc())
            .all()
        )
        return [{"id": r[0], "text": r[0]} for r in rows if (r[0] or "").strip()]
    if type == "envanter":
        q = db.query(Inventory)
        if exclude_id:
            q = q.filter(Inventory.id != exclude_id)
        rows = q.order_by(Inventory.id.desc()).all()
        return [{"id": r.no, "text": r.no} for r in rows]
    return []


@router.post("/assign", name="inventory.assign")
def assign(
    item_id: int = Form(...),
    fabrika: str | None = Form(None),
    departman: str | None = Form(None),
    sorumlu_personel: str | None = Form(None),
    bagli_envanter_no: str | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    item = db.query(Inventory).get(item_id)
    if not item:
        raise HTTPException(404)

    before = {
        "fabrika": item.fabrika,
        "departman": item.departman,
        "sorumlu_personel": item.sorumlu_personel,
        "bagli_envanter_no": item.bagli_envanter_no,
    }

    item.fabrika = fabrika or item.fabrika
    item.departman = departman or item.departman
    item.sorumlu_personel = sorumlu_personel or item.sorumlu_personel
    item.bagli_envanter_no = bagli_envanter_no or item.bagli_envanter_no

    db.add(item)
    db.add(
        InventoryLog(
            inventory_id=item.id,
            action="assign",
            before_json=before,
            after_json={
                "fabrika": item.fabrika,
                "departman": item.departman,
                "sorumlu_personel": item.sorumlu_personel,
                "bagli_envanter_no": item.bagli_envanter_no,
            },
            note=f"{user.username} tarafından atama",
            created_at=datetime.utcnow(),
            actor=user.username,
        )
    )
    db.commit()
    return JSONResponse({"ok": True})


@router.get("/{item_id}/edit", name="inventory.edit")
def edit_page(
    request: Request,
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    item = db.query(Inventory).get(item_id)
    if not item:
        raise HTTPException(404)
    return templates.TemplateResponse(
        "inventory/edit.html", {"request": request, "item": item, "item_id": item.id}
    )


@router.post("/{item_id}/edit", name="inventory.edit_post")
async def edit_post(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    form = dict(await request.form())
    item = db.query(Inventory).get(item_id)
    if not item:
        raise HTTPException(404)

    before = item.to_dict() if hasattr(item, "to_dict") else None
    for k in [
        "fabrika",
        "departman",
        "sorumlu_personel",
        "bagli_envanter_no",
        "marka",
        "model",
        "kullanim_alani",
        "ifs_no",
        "not",
    ]:
        if k in form:
            setattr(item, "not_" if k == "not" else k, form[k] or None)

    db.add(item)
    db.add(
        InventoryLog(
            inventory_id=item.id,
            action="edit",
            before_json=before,
            after_json=item.to_dict() if hasattr(item, "to_dict") else None,
            note=f"{user.username} düzenledi",
            created_at=datetime.utcnow(),
            actor=user.username,
        )
    )
    db.commit()
    return RedirectResponse(
        url=request.url_for("inventory.detail", item_id=item.id), status_code=303
    )


@router.post("/scrap", name="inventory.scrap")
def scrap(
    item_id: int = Form(...),
    aciklama: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    item = db.query(Inventory).get(item_id)
    if not item:
        raise HTTPException(404)

    s = ScrapItem.from_inventory(item, reason=aciklama, actor=user.username)
    db.add(s)

    item.durum = "hurda"
    db.add(item)

    db.add(
        InventoryLog(
            inventory_id=item.id,
            action="scrap",
            before_json=None,
            after_json={"durum": "hurda", "aciklama": aciklama},
            note="Hurdalara taşındı",
            created_at=datetime.utcnow(),
            actor=user.username,
        )
    )
    db.commit()
    return JSONResponse({"ok": True})


@router.get("/hurdalar", name="inventory.hurdalar")
def hurdalar_listesi(
    request: Request, db: Session = Depends(get_db), user=Depends(current_user)
):
    hurdalar = db.query(Inventory).filter(Inventory.durum == "hurda").all()
    logs_map = {
        item.id: (
            db.query(InventoryLog)
            .filter(InventoryLog.inventory_id == item.id)
            .order_by(InventoryLog.created_at.desc())
            .all()
        )
        for item in hurdalar
    }
    return templates.TemplateResponse(
        "hurdalar.html",
        {"request": request, "hurdalar": hurdalar, "logs_map": logs_map},
    )
