from datetime import date, datetime
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Brand,
    Factory,
    HardwareType,
    Inventory,
    InventoryLog,
    License,
    LicenseLog,
    Model,
    ScrapItem,
    ScrapPrinter,
    StockTotal,
    UsageArea,
    User,
)
from security import current_user
from utils.faults import FAULT_STATUS_SCRAP, resolve_fault
from utils.http import get_request_user_name
from utils.stock_log import create_stock_log
from utils.template_filters import register_filters

templates = register_filters(Jinja2Templates(directory="templates"))


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
        ws.append(
            [
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
            ]
        )

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    headers = {"Content-Disposition": "attachment; filename=inventory.xlsx"}
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/import", response_class=PlainTextResponse)
async def import_inventory(file: UploadFile = File(...)):
    return f"Received {file.filename}, but import is not implemented."
def _inventory_lookups(db: Session) -> dict[str, Any]:
    fabrika = [
        row.name
        for row in db.query(Factory).order_by(Factory.name.asc()).all()
        if (row.name or "").strip()
    ]
    departman_rows = (
        db.query(Inventory.departman)
        .filter(Inventory.departman.isnot(None))
        .distinct()
        .order_by(Inventory.departman.asc())
        .all()
    )
    departman = [val[0] for val in departman_rows if (val[0] or "").strip()]
    donanim_tipi = [
        row.name
        for row in db.query(HardwareType).order_by(HardwareType.name.asc()).all()
    ]
    marka = [row.name for row in db.query(Brand).order_by(Brand.name.asc()).all()]
    personel = [
        name
        for name in [
            (user.full_name or user.username or "").strip()
            for user in db.query(User)
            .order_by(User.full_name.asc(), User.username.asc())
            .all()
        ]
        if name
    ]
    envanterler = [
        {
            "envanter_no": inv.no,
            "bilgisayar_adi": inv.bilgisayar_adi or "",
        }
        for inv in (
            db.query(Inventory)
            .filter(Inventory.durum != "hurda")
            .order_by(Inventory.no.asc())
            .all()
        )
    ]
    return {
        "fabrika": fabrika,
        "departman": departman,
        "donanim_tipi": donanim_tipi,
        "marka": marka,
        "personel": personel,
        "envanterler": envanterler,
    }


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
    lookups = _inventory_lookups(db)
    current_id = request.query_params.get("id") or request.query_params.get("item")
    try:
        current_id_int = int(current_id) if current_id else None
    except (TypeError, ValueError):
        current_id_int = None
    current_item = db.get(Inventory, current_id_int) if current_id_int else None
    context = {
        "request": request,
        "items": items,
        "lookups": lookups,
        "current_id": current_id_int,
        "current_item": current_item,
    }
    return templates.TemplateResponse("inventory/index.html", context)


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
        islem_yapan=get_request_user_name(request),
    )
    db.add(rec)
    db.commit()
    return RedirectResponse(url="/inventory", status_code=303)


@router.post("/new", name="inventory.new_post")
async def new_post(
    request: Request, db: Session = Depends(get_db), user=Depends(current_user)
):
    form = dict(await request.form())

    brand = db.get(Brand, int(form.get("marka"))) if form.get("marka") else None
    model_obj = db.get(Model, int(form.get("model"))) if form.get("model") else None
    usage = (
        db.get(UsageArea, int(form.get("kullanim_alani")))
        if form.get("kullanim_alani")
        else None
    )
    hw = (
        db.get(HardwareType, int(form.get("donanim_tipi")))
        if form.get("donanim_tipi")
        else None
    )
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


@router.get("/{item_id:int}/detail", name="inventory.detail")
def detail(
    request: Request,
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
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
    lisanslar = (
        db.query(License)
        .filter(
            (License.inventory_id == item_id) | (License.bagli_envanter_no == item.no)
        )
        .all()
    )
    return templates.TemplateResponse(
        "inventory_detail.html",
        {
            "request": request,
            "inv": item,
            "logs": logs,
            "lisanslar": lisanslar,
        },
    )


@router.get("/{item_id:int}", name="inventory.detail_short", include_in_schema=False)
def detail_short(
    request: Request,
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    return detail(request, item_id, db, user)


@router.get("/assign/sources", name="inventory.assign_sources")
def assign_sources(
    type: str | None = None,
    exclude_id: int | None = None,
    db: Session = Depends(get_db),
):
    if not type:
        users = db.query(User).order_by(User.full_name.asc()).all()
        inv_q = db.query(Inventory).filter(Inventory.durum != "hurda")
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
        q = db.query(Inventory).filter(Inventory.durum != "hurda")
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
    item = db.get(Inventory, item_id)
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


@router.get("/{item_id:int}/edit", name="inventory.edit")
def edit_page(
    request: Request,
    item_id: int,
    modal: bool = False,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    item = db.get(Inventory, item_id)
    if not item:
        raise HTTPException(404)
    return templates.TemplateResponse(
        "inventory/edit.html",
        {"request": request, "item": item, "item_id": item.id, "modal": modal},
    )


@router.post("/{item_id:int}/edit", name="inventory.edit_post")
async def edit_post(
    item_id: int,
    request: Request,
    modal: bool = False,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    form = dict(await request.form())
    item = db.get(Inventory, item_id)
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
    if modal:
        return HTMLResponse(
            "<script>window.parent.postMessage('modal-close','*');</script>"
        )
    return RedirectResponse(
        url=request.url_for("inventory.detail", item_id=item.id), status_code=303
    )


@router.get("/{item_id:int}/stock", name="inventory.stock")
def stock_entry(
    item_id: int, db: Session = Depends(get_db), user=Depends(current_user)
):
    item = db.get(Inventory, item_id)
    if not item:
        raise HTTPException(404)
    actor = getattr(user, "full_name", None) or user.username
    donanim_tipi = item.donanim_tipi or "Envanter"

    # Stoka alınan envanter için ilişkili personel/makina bilgilerini sıfırla
    item.sorumlu_personel = None
    item.bagli_envanter_no = None
    item.fabrika = "Baylan 3"
    item.departman = "Bilgi İşlem"

    create_stock_log(
        db,
        donanim_tipi=donanim_tipi,
        miktar=1,
        ifs_no=item.ifs_no,
        marka=item.marka,
        model=item.model,
        islem="girdi",
        actor=actor,
        source_type="envanter",
        source_id=item.id,
    )

    total = db.get(StockTotal, donanim_tipi) or StockTotal(
        donanim_tipi=donanim_tipi, toplam=0
    )
    total.toplam += 1
    db.merge(total)

    after_data = item.to_dict() if hasattr(item, "to_dict") else None
    if after_data:
        for k, v in list(after_data.items()):
            if isinstance(v, datetime):
                after_data[k] = v.isoformat()
    db.add(
        InventoryLog(
            inventory_id=item.id,
            action="stock",
            before_json=None,
            after_json=after_data,
            note="Stok girişi yapıldı",
            created_at=datetime.utcnow(),
            actor=actor,
        )
    )
    db.commit()
    return RedirectResponse(url="/stock?tab=status&module=inventory", status_code=303)


@router.post("/scrap", name="inventory.scrap")
def scrap(
    item_id: int = Form(...),
    aciklama: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    item = db.get(Inventory, item_id)
    if not item:
        raise HTTPException(404)

    s = ScrapItem.from_inventory(item, reason=aciklama, actor=user.username)
    db.add(s)

    item.durum = "hurda"
    db.add(item)

    for lic in list(item.licenses):
        lic.sorumlu_personel = None
        lic.bagli_envanter_no = None
        lic.inventory_id = None
        db.add(
            LicenseLog(
                license_id=lic.id,
                islem="ATAMA",
                detay="Envanter hurdaya ayrıldığı için lisans bağlantısı kaldırıldı",
                islem_yapan=user.username,
            )
        )

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
    resolve_fault(
        db,
        "inventory",
        entity_id=item.id,
        status=FAULT_STATUS_SCRAP,
        actor=getattr(user, "full_name", None) or user.username,
        note="Hurdaya ayırma işlemi",
    )
    db.commit()
    return JSONResponse({"ok": True})


@router.get("/hurdalar", name="inventory.hurdalar")
def hurdalar_listesi(
    request: Request,
    tur: str = "envanter",
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    def to_datetime(value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        return None

    def format_display_date(value):
        if isinstance(value, datetime):
            return value.strftime("%d.%m.%Y %H:%M")
        if isinstance(value, date):
            return value.strftime("%d.%m.%Y")
        return "-"

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
    printer_scraps = (
        db.query(ScrapPrinter).order_by(ScrapPrinter.created_at.desc()).all()
    )

    combined_scraps = []

    for item in hurdalar:
        display_title = " ".join(filter(None, [item.marka, item.model])).strip() or "-"
        details = [
            {"label": "Envanter No", "value": item.no or "-"},
            {"label": "Seri No", "value": item.seri_no or "-"},
            {
                "label": "Departman",
                "value": item.departman or item.fabrika or "-",
            },
            {"label": "Sorumlu", "value": item.sorumlu_personel or "-"},
            {"label": "Bağlı Envanter", "value": item.bagli_envanter_no or "-"},
            {
                "label": "Kullanım Alanı",
                "value": item.kullanim_alani or "-",
            },
        ]

        if item.not_:
            details.append({"label": "Not", "value": item.not_})

        search_text = " ".join(
            filter(
                None,
                [
                    "envanter",
                    item.no,
                    item.marka,
                    item.model,
                    item.seri_no,
                    item.departman,
                    item.sorumlu_personel,
                    item.bagli_envanter_no,
                    item.kullanim_alani,
                    item.not_,
                ],
            )
        ).lower()

        combined_scraps.append(
            {
                "type": "envanter",
                "type_label": "Envanter",
                "title": display_title,
                "subtitle": f"Envanter No: {item.no}",
                "details": details,
                "logs": logs_map[item.id],
                "display_date": format_display_date(item.tarih),
                "sort_date": to_datetime(item.tarih),
                "detail_url": f"/scrap/inventory/{item.id}",
                "search": search_text,
            }
        )

    for row in license_scraps:
        details = [
            {"label": "Lisans ID", "value": row.id},
            {"label": "Lisans Key", "value": row.lisans_key or "-"},
            {"label": "Sorumlu", "value": row.sorumlu_personel or "-"},
            {"label": "Bağlı Envanter", "value": row.bagli_envanter_no or "-"},
            {"label": "IFS No", "value": row.ifs_no or "-"},
        ]

        if row.notlar:
            details.append({"label": "Not", "value": row.notlar})

        title = row.lisans_adi or f"Lisans #{row.id}"
        subtitle = f"Lisans ID: {row.id}"

        search_text = " ".join(
            filter(
                None,
                [
                    "lisans",
                    str(row.id),
                    row.lisans_adi,
                    row.lisans_key,
                    row.sorumlu_personel,
                    row.bagli_envanter_no,
                    row.ifs_no,
                    row.notlar,
                ],
            )
        ).lower()

        combined_scraps.append(
            {
                "type": "lisans",
                "type_label": "Lisans",
                "title": title,
                "subtitle": subtitle,
                "details": details,
                "logs": [],
                "display_date": format_display_date(row.tarih),
                "sort_date": to_datetime(row.tarih),
                "detail_url": f"/lisans/detail/{row.id}",
                "search": search_text,
            }
        )

    for scrap in printer_scraps:
        snapshot = scrap.snapshot or {}
        marka = snapshot.get("marka")
        model = snapshot.get("model")
        seri = snapshot.get("seri_no")
        title = " ".join(filter(None, [marka, model])).strip()
        if not title:
            title = f"Yazıcı #{scrap.printer_id}"

        subtitle = f"Seri No: {seri or '-'}"

        details = [
            {"label": "Yazıcı ID", "value": f"#{scrap.printer_id}"},
            {"label": "Seri No", "value": seri or "-"},
            {"label": "Fabrika", "value": snapshot.get("fabrika") or "-"},
            {
                "label": "Kullanım Alanı",
                "value": snapshot.get("kullanim_alani") or "-",
            },
            {
                "label": "Sorumlu",
                "value": snapshot.get("sorumlu_personel") or "-",
            },
            {
                "label": "Bağlı Envanter",
                "value": snapshot.get("bagli_envanter_no") or "-",
            },
        ]

        reason = scrap.reason or snapshot.get("notlar") or snapshot.get("not")
        if reason:
            details.append({"label": "Sebep", "value": reason})

        search_text = " ".join(
            filter(
                None,
                [
                    "yazici",
                    str(scrap.printer_id),
                    marka,
                    model,
                    seri,
                    snapshot.get("fabrika"),
                    snapshot.get("kullanim_alani"),
                    snapshot.get("sorumlu_personel"),
                    snapshot.get("bagli_envanter_no"),
                    reason,
                ],
            )
        ).lower()

        combined_scraps.append(
            {
                "type": "yazici",
                "type_label": "Yazıcı",
                "title": title,
                "subtitle": subtitle,
                "details": details,
                "logs": [],
                "display_date": format_display_date(scrap.created_at),
                "sort_date": to_datetime(scrap.created_at),
                "detail_url": f"/printers/{scrap.printer_id}",
                "search": search_text,
            }
        )

    combined_scraps.sort(
        key=lambda item: item["sort_date"] or datetime.min,
        reverse=True,
    )

    return templates.TemplateResponse(
        "hurdalar.html",
        {
            "request": request,
            "combined_scraps": combined_scraps,
            "tur": tur,
        },
    )
