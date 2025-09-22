from fastapi import HTTPException
from sqlalchemy.orm import Session


def validate_adet(adet: int) -> None:
    """Ensure that the given quantity is a positive integer."""
    if adet <= 0:
        raise HTTPException(status_code=400, detail="Adet 0'dan büyük olmalı")


def get_or_404(db: Session, model, id: int, message: str = "Kayıt bulunamadı"):
    """Return the object with ``id`` from ``model`` or raise a 404 error."""
    obj = db.get(model, id)
    if not obj:
        raise HTTPException(status_code=404, detail=message)
    return obj
