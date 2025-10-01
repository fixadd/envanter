from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Bilgi, BilgiKategori, UserPinLimit
from security import SessionUser, current_user
from utils.template_filters import register_filters

router = APIRouter(prefix="/bilgiler", tags=["Bilgiler"])
templates = register_filters(Jinja2Templates(directory="templates"))

UPLOAD_DIR = Path("static/uploads/bilgiler")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB


class PinPayload(BaseModel):
    pin: bool


def _serialize_bilgi_list(
    items: list[Bilgi],
    current_user_id: int,
) -> tuple[list[Bilgi], list[Bilgi]]:
    pinned = []
    others = []
    for item in items:
        if item.is_pinned and item.pinned_by == current_user_id:
            pinned.append(item)
        else:
            others.append(item)
    return pinned, others


def _save_photo_path(filename: str) -> Path:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Desteklenmeyen dosya formatı")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid4().hex}{ext}"
    return UPLOAD_DIR / unique_name


async def _store_photo(file: UploadFile) -> str:
    if not file.filename:
        return ""

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail="Sadece jpg, jpeg, png veya gif yükleyebilirsiniz"
        )

    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="Dosya boyutu 5MB'ı geçemez")

    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, detail="Sadece görsel dosyaları yükleyebilirsiniz"
        )

    target = _save_photo_path(file.filename)
    target.write_bytes(data)
    return str(target.relative_to(Path("static")))


def _remove_photo(path_str: str | None) -> None:
    if not path_str:
        return
    candidate = Path("static") / path_str
    if candidate.exists() and candidate.is_file():
        try:
            candidate.unlink()
        except OSError:
            pass


@router.get("", response_class=HTMLResponse)
def bilgi_index(
    request: Request,
    kategori: int | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    query = (
        db.query(Bilgi)
        .options(joinedload(Bilgi.kategori), joinedload(Bilgi.author))
        .order_by(Bilgi.created_at.desc())
    )

    if kategori:
        query = query.filter(Bilgi.kategori_id == kategori)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Bilgi.baslik.ilike(like), Bilgi.icerik.ilike(like)))

    items = query.all()
    pinned_items, other_items = _serialize_bilgi_list(items, user.id)

    categories = db.query(BilgiKategori).order_by(BilgiKategori.ad.asc()).all()

    return templates.TemplateResponse(
        "bilgiler/index.html",
        {
            "request": request,
            "categories": categories,
            "pinned_items": pinned_items,
            "other_items": other_items,
            "selected_category": kategori or "",
            "search_query": q or "",
            "session_user": user,
        },
    )


@router.post("/ekle")
async def bilgi_create(
    request: Request,
    baslik: str = Form(...),
    kategori_id: str | None = Form(None),
    icerik: str = Form(""),
    foto: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    title = baslik.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Başlık zorunludur")

    content = (icerik or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="İçerik zorunludur")

    kategori_ref = None
    if kategori_id:
        try:
            kategori_key = int(kategori_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Geçersiz kategori seçimi")

        kategori_ref = db.get(BilgiKategori, kategori_key)
        if not kategori_ref:
            raise HTTPException(status_code=400, detail="Geçersiz kategori seçimi")

    photo_path = None
    if foto and foto.filename:
        photo_path = await _store_photo(foto)

    now = datetime.utcnow()
    bilgi = Bilgi(
        baslik=title,
        kategori_id=kategori_ref.id if kategori_ref else None,
        icerik=content,
        foto_yolu=photo_path,
        kullanici_id=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(bilgi)
    db.commit()
    db.refresh(bilgi)

    return JSONResponse(
        {"ok": True, "id": bilgi.id}, status_code=status.HTTP_201_CREATED
    )


@router.put("/{bilgi_id}/pin")
def bilgi_pin(
    bilgi_id: int,
    payload: PinPayload,
    db: Session = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    bilgi = db.get(Bilgi, bilgi_id)
    if not bilgi:
        raise HTTPException(status_code=404, detail="Bilgi bulunamadı")

    if bilgi.kullanici_id != user.id:
        raise HTTPException(
            status_code=403, detail="Sadece kendi kayıtlarınızı sabitleyebilirsiniz"
        )

    limit = db.get(UserPinLimit, user.id)
    if not limit:
        limit = UserPinLimit(user_id=user.id, pin_count=0)

    if payload.pin:
        if bilgi.is_pinned and bilgi.pinned_by == user.id:
            return {"pinned": True, "pin_count": limit.pin_count}
        if limit.pin_count >= 3:
            raise HTTPException(
                status_code=400, detail="En fazla 3 bilgi sabitleyebilirsiniz"
            )
        bilgi.is_pinned = True
        bilgi.pinned_by = user.id
        bilgi.pinned_at = datetime.utcnow()
        limit.pin_count += 1
    else:
        if bilgi.is_pinned and limit.pin_count > 0:
            limit.pin_count -= 1
        bilgi.is_pinned = False
        bilgi.pinned_by = None
        bilgi.pinned_at = None

    bilgi.updated_at = datetime.utcnow()
    db.add_all([bilgi, limit])
    db.commit()
    db.refresh(limit)

    return {"pinned": bilgi.is_pinned, "pin_count": limit.pin_count}


@router.delete("/{bilgi_id}")
def bilgi_delete(
    bilgi_id: int,
    db: Session = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    bilgi = db.get(Bilgi, bilgi_id)
    if not bilgi:
        raise HTTPException(status_code=404, detail="Bilgi bulunamadı")

    is_owner = bilgi.kullanici_id == user.id
    if not (is_owner or user.role == "admin"):
        raise HTTPException(status_code=403, detail="Silme yetkiniz yok")

    photo_path = bilgi.foto_yolu
    was_pinned_by_owner = bilgi.is_pinned and bilgi.pinned_by == bilgi.kullanici_id

    if was_pinned_by_owner:
        limit = db.get(UserPinLimit, bilgi.kullanici_id)
        if limit and limit.pin_count > 0:
            limit.pin_count -= 1
            db.add(limit)

    db.delete(bilgi)
    db.commit()

    _remove_photo(photo_path)
    return {"ok": True}
