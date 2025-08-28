from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import (
    JSONResponse,
    RedirectResponse,
    PlainTextResponse,
    StreamingResponse,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from datetime import datetime
from fastapi.templating import Jinja2Templates
from io import BytesIO

from database import get_db
from models import (
    Inventory,
    InventoryLog,
    ScrapItem,
    User,
    Factory,
    Brand,
    Model,
    UsageArea,
    HardwareType,
    License,
    ScrapPrinter,
)
from security import current_user
from utils.i18n import humanize_log

templates = Jinja2Templates(directory="templates")
templates.env.filters["humanize_log"] = humanize_log

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/export")
async def export_inventory(db: Session = Depends(get_db)):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    headers = [
        "ID",
        "No",
        "Fabrika",
        "Departman",
        "Donanim Tipi",
        "Bilgisayar Adı",
        "Marka",
        "Model",
        "Seri No",
        "Sorumlu Personel",
        "Bağlı Envanter No",
        "Kullanım Alanı",
        "IFS No",
        "Tarih",
        "İşlem Yapan",
        "Durum",
        "Not",
    ]
    ws.append(headers)

    items = db.query(Inventory).order_by(Inventory.id.asc()).all()
    for i in items:
        ws.append([
            i.id,
            i.no,
            i.fabrika,
            i.departman,
            i.donanim_tipi,
            i.bilgisayar_adi,
            i.marka,
            i.model,
            i.seri_no,
            i.sorumlu_personel,
            i.bagli_envanter_no,
            i.kullanim_alani,
            i.ifs_no,
            i.tarih,
            i.islem_yapan,
            i.durum,
            i.not_,
        ])

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    headers = {
        "Content-Disposition": "attachment; filename=inventory.xlsx"
    }
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/import", response_class=PlainTextResponse)
async def import_inventory(file: UploadFile = File(...)):
    return f"Received {file.filename}, but import is not implemented."


def current_full_name(request: Request) -> str:
    return (
        request.session.get("full_name")
        or getattr(getattr(request, "user", None), "full_name", None)
        or "Bilinmeyen Kullanıcı"
    )

@router.get("", name="inventory.list")
def list_items(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
  items = (
    db.query(Inventory)
    .filter(Inventory.durum != "hurda")
    .order_by(Inventory.id.desc())
    .all()
  )
  return templates.TemplateResponse("inventory_list.html", {"request": request, "items": items})

@router.get("/new", name="inventory.new")
def new_page(request: Request, user=Depends(current_user)):
  return templates.TemplateResponse("inventory_add.html", {"request": request})


@router.post("/create")
def create_inventory(
    request: Request,
    envanter_no: str = Form(...),
    fabrika: str = Form(...),
    departman: str = Form(...),
    donanim_tipi: str = Form(...),
    bilgisayar_adi: str = Form(...),
    marka: str = Form(...),
    model: str = Form(...),
    seri_no: str = Form(...),
    sorumlu_personel: str = Form(...),
    bagli_envanter_no: str = Form(None),
    notlar: str = Form(None),
    ifs_no: str = Form(None),
    db: Session = Depends(get_db),
):
    rec = Inventory(
        no=envanter_no,
        fabrika=fabrika,
        departman=departman,
        donanim_tipi=donanim_tipi,
        bilgisayar_adi=bilgisayar_adi,
        marka=marka,
        model=model,
        seri_no=seri_no,
        sorumlu_personel=sorumlu_personel,
        bagli_envanter_no=bagli_envanter_no,
        not_=notlar,
        ifs_no=ifs_no,
        tarih=datetime.now(),
        islem_yapan=current_full_name(request),
    )
    db.add(rec)
    db.commit()
    return RedirectResponse(url="/inventory", status_code=303)

@router.post("/new", name="inventory.new_post")
async def new_post(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
  form = dict(await request.form())

  brand = db.get(Brand, int(form.get("marka"))) if form.get("marka") else None
  model_obj = db.get(Model, int(form.get("model"))) if form.get("model") else None
  usage = db.get(UsageArea, int(form.get("kullanim_alani"))) if form.get("kullanim_alani") else None
  hw = db.get(HardwareType, int(form.get("donanim_tipi"))) if form.get("donanim_tipi") else None
  factory = db.get(Factory, int(form.get("fabrika"))) if form.get("fabrika") else None

  inv = Inventory(
    no=form.get("no") or f"INV{int(datetime.utcnow().timestamp())}",
    fabrika=factory.name if factory else None,
    departman=form.get("departman"),
    donanim_tipi=hw.name if hw else None,
    bilgisayar_adi=form.get("bilgisayar_adi"),
    marka=brand.name if brand else None,
    model=model_obj.name if model_obj else None,
    seri_no=form.get("seri_no"),
    kullanim_alani=usage.name if usage else None,
    ifs_no=form.get("ifs_no"),
    not_=form.get("not") or None,
    tarih=datetime.utcnow(),
    islem_yapan=getattr(user, "full_name", None) or user.username,
  )
  db.add(inv)
  db.commit()
  db.refresh(inv)
  db.add(InventoryLog(
    inventory_id=inv.id,
    action="create",
    before_json=None,
    after_json=inv.to_dict() if hasattr(inv, "to_dict") else None,
    note="Oluşturuldu",
    created_at=datetime.utcnow(),
    actor=user.username,
  ))
  db.commit()
  return RedirectResponse(url=request.url_for("inventory.detail", item_id=inv.id), status_code=303)

@router.get("/{item_id:int}/detail", name="inventory.detail")
def detail(request: Request, item_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    stmt = select(Inventory).where(Inventory.id == item_id)
    item = db.execute(stmt).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
    logs = (
        db.query(InventoryLog)
        .filter(InventoryLog.inventory_id == item_id)
        .order_by(InventoryLog.created_at.desc())
        .all()
    )
    lisanslar = db.query(License).filter(
        (License.inventory_id == item_id) | (License.bagli_envanter_no == item.no)
    ).all()
    return templates.TemplateResponse(
        "inventory_detail.html",
        {
            "request": request,
            "inv": item,
            "logs": logs,
            "lisanslar": lisanslar,
            "loglar": logs,
        },
    )

@router.get("/{item_id:int}", name="inventory.detail_short", include_in_schema=False)
def detail_short(request: Request, item_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
  return detail(request, item_id, db, user)

@router.get("/assign/sources", name="inventory.assign_sources")
def assign_sources(
    type: str | None = None,
    exclude_id: int | None = None,
    db: Session = Depends(get_db),
):
    if not type:
        users = db.query(User).order_by(User.full_name.asc()).all()
        inv_q = db.query(Inventory)
        if exclude_id:
            inv_q = inv_q.filter(Inventory.id != exclude_id)
        inventories = inv_q.order_by(Inventory.id.desc()).all()
        return {
            "users": [
                {
                    "id": u.full_name or u.username,
                    "text": u.full_name or u.username,
                }
                for u in users
                if (u.full_name or u.username or "").strip()
            ],
            "inventories": [
                {
                    "id": r.id,
                    "envanter_no": r.no,
                    "marka": r.marka,
                    "model": r.model,
                }
                for r in inventories
            ],
        }
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

@router.get("/{item_id:int}/edit", name="inventory.edit")
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

@router.post("/{item_id:int}/edit", name="inventory.edit_post")
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
  logs_map = {
    item.id: (
      db.query(InventoryLog)
      .filter(InventoryLog.inventory_id == item.id)
      .order_by(InventoryLog.created_at.desc())
      .all()
    )
    for item in hurdalar
  }

  license_scraps = db.query(License).filter(License.durum == "hurda").all()
  printer_scraps = db.query(ScrapPrinter).order_by(ScrapPrinter.created_at.desc()).all()

  return templates.TemplateResponse(
    "hurdalar.html",
    {
      "request": request,
      "hurdalar": hurdalar,
      "logs_map": logs_map,
      "license_scraps": license_scraps,
      "printer_scraps": printer_scraps,
    },
  )
