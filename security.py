# security.py
from dataclasses import dataclass, field

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth import get_user_by_id
from database import get_db


@dataclass
class SessionUser:
    id: int
    username: str
    role: str
    full_name: str | None = field(default=None)
    email: str | None = field(default=None)

    def __post_init__(self) -> None:
        if self.full_name is None:
            self.full_name = self.username


def current_user(request: Request, db: Session = Depends(get_db)) -> SessionUser:
    user_id = request.session.get("user_id")
    if not user_id:
        # Özel sinyal: app.py içinde yakalayıp /login'e yönlendireceğiz
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER, detail="redirect:/login"
        )
    u = get_user_by_id(db, int(user_id))
    if not u:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER, detail="redirect:/login"
        )
    return SessionUser(
        u.id,
        u.username,
        getattr(u, "role", "admin"),
        u.full_name,
        getattr(u, "email", None),
    )


def require_roles(*roles: str):
    def dep(user: SessionUser = Depends(current_user)) -> SessionUser:
        if roles and user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return user

    return dep
