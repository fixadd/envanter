from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from datetime import datetime
from fastapi.templating import Jinja2Templates

from database import get_db
from models import Inventory, InventoryLog, ScrapItem, User
from security import current_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.get("", name="inventory.list")
def list_items(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
  items = db.query(Inventory).order_by(Inventory.id.desc()).all()
  return templates.TemplateResponse("inventory_list.html", {"request": request, "items": items})

@router.get("/{item_id}/detail", name="inventory.detail")
def detail(request: Request, item_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
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
def assign_sources(type: str, exclude_id: int | None = None, db: Session = Depends(get_db), user=Depends(current_user)):
  if type == "fabrika":
    vals = db.query(Inventory.fabrika).distinct().all()
    data = [{"value": v[0], "label": v[0]} for v in vals if v[0]]
  elif type == "departman":
    vals = db.query(Inventory.departman).distinct().all()
    data = [{"value": v[0], "label": v[0]} for v in vals if v[0]]
  elif type == "users":
    users = db.query(User).order_by(User.full_name).all()
    data = [{"value": u.full_name, "label": u.full_name} for u in users]
  elif type == "envanter":
    q = db.query(Inventory.id, Inventory.no)
    if exclude_id:
      q = q.filter(Inventory.id != exclude_id)
    data = [{"value": no, "label": f"{no}"} for (_id, no) in q.all()]
  else:
    data = []
  return JSONResponse(data)

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

  item.fabrika = (fabrika or item.fabrika)
  item.departman = (departman or item.departman)
  item.sorumlu_personel = (sorumlu_personel or item.sorumlu_personel)
  item.bagli_envanter_no = (bagli_envanter_no or item.bagli_envanter_no)

  db.add(item)
  db.add(InventoryLog(
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
    actor=user.username
  ))
  db.commit()
  return JSONResponse({"ok": True})

@router.get("/{item_id}/edit", name="inventory.edit")
def edit_page(request: Request, item_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
  item = db.query(Inventory).get(item_id)
  if not item:
    raise HTTPException(404)
  return templates.TemplateResponse("inventory_edit.html", {"request": request, "item": item})

@router.post("/{item_id}/edit", name="inventory.edit_post")
async def edit_post(item_id: int, request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
  form = dict(await request.form())
  item = db.query(Inventory).get(item_id)
  if not item:
    raise HTTPException(404)

  before = item.to_dict() if hasattr(item, "to_dict") else None
  for k in ["fabrika","departman","sorumlu_personel","bagli_envanter_no","marka","model","kullanim_alani","ifs_no","not"]:
    if k in form:
      setattr(item, "not_" if k=="not" else k, form[k] or None)

  db.add(item)
  db.add(InventoryLog(
    inventory_id=item.id,
    action="edit",
    before_json=before,
    after_json=item.to_dict() if hasattr(item,"to_dict") else None,
    note=f"{user.username} düzenledi",
    created_at=datetime.utcnow(),
    actor=user.username
  ))
  db.commit()
  return RedirectResponse(url=request.url_for("inventory.detail", item_id=item.id), status_code=303)

@router.post("/scrap", name="inventory.scrap")
def scrap(item_id: int = Form(...), aciklama: str = Form(""), db: Session = Depends(get_db), user=Depends(current_user)):
  item = db.query(Inventory).get(item_id)
  if not item:
    raise HTTPException(404)

  s = ScrapItem.from_inventory(item, reason=aciklama, actor=user.username)
  db.add(s)

  item.durum = "hurda"
  db.add(item)

  db.add(InventoryLog(
    inventory_id=item.id,
    action="scrap",
    before_json=None,
    after_json={"durum": "hurda", "aciklama": aciklama},
    note="Hurdalara taşındı",
    created_at=datetime.utcnow(),
    actor=user.username
  ))
  db.commit()
  return JSONResponse({"ok": True})

@router.get("/hurdalar", name="inventory.hurdalar")
def hurdalar_listesi(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
  hurdalar = db.query(Inventory).filter(Inventory.durum == "hurda").all()
  return templates.TemplateResponse("hurdalar.html", {"request": request, "hurdalar": hurdalar})
