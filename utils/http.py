from typing import Mapping, MutableMapping, Optional

from fastapi import HTTPException, Request
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


def get_request_user_name(
    request: Request, *, default: str = "Bilinmeyen Kullanıcı"
) -> str:
    """Return a display name for the current request's user.

    ``SessionMiddleware`` stores the authenticated user's name under
    ``request.session['full_name']`` while FastAPI's authentication middleware
    adds the user object to ``request.scope['user']``.  Accessing
    ``request.user`` raises an ``AssertionError`` if the authentication
    middleware is not installed, so we read from ``scope`` directly.  This
    keeps the helper safe to call in tests or lightweight deployments.
    """

    session: Optional[MutableMapping[str, str]]
    try:
        session = request.session  # type: ignore[attr-defined]
    except AttributeError:
        session = None

    session_name = session.get("full_name") if isinstance(session, Mapping) else None

    scope_user = request.scope.get("user") if hasattr(request, "scope") else None
    scope_name = getattr(scope_user, "full_name", None)

    return session_name or scope_name or default
