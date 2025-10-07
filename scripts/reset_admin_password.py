"""Utility for resetting a user's password from the command line."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

from dotenv import load_dotenv
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password
from models import SessionLocal, User


def reset_password(
    username: str,
    password: str,
    *,
    db: Session | None = None,
) -> bool:
    """Update ``username`` with a freshly hashed ``password``.

    Parameters
    ----------
    username:
        The account whose password should be updated. Comparison is case
        insensitive and leading / trailing whitespace is ignored.
    password:
        The new plaintext password. An empty value raises :class:`ValueError`.
    db:
        Optional SQLAlchemy session. When omitted a dedicated session is
        created for the duration of the call.

    Returns
    -------
    bool
        ``True`` if the user was found and updated, otherwise ``False``.
    """

    normalized = (username or "").strip()
    if not normalized:
        raise ValueError("username cannot be blank")

    if not password:
        raise ValueError("password cannot be empty")

    own_session = db is None
    session = db or SessionLocal()

    try:
        user = (
            session.query(User)
            .filter(func.lower(User.username) == normalized.lower())
            .first()
        )
        if not user:
            return False

        user.password_hash = hash_password(password)
        session.add(user)
        session.commit()
        if own_session:
            session.refresh(user)
        return True
    finally:
        if own_session:
            session.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reset an application's user password.",
    )
    parser.add_argument(
        "-u",
        "--username",
        default=os.getenv("DEFAULT_ADMIN_USERNAME", "admin"),
        help="Kullanıcı adı (varsayılan: %(default)s)",
    )
    parser.add_argument(
        "-p",
        "--password",
        help=(
            "Yeni parolayı belirtin. Eğer verilmezse DEFAULT_ADMIN_PASSWORD "
            "ortam değişkeni kullanılmaya çalışılır."
        ),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    load_dotenv()
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    password = args.password or os.getenv("DEFAULT_ADMIN_PASSWORD", "")
    if not password:
        parser.error(
            "Parola belirtilmedi. --password kullanın ya da "
            "DEFAULT_ADMIN_PASSWORD ortam değişkenini ayarlayın."
        )

    try:
        updated = reset_password(args.username, password)
    except ValueError as exc:  # pragma: no cover - parser enforces inputs
        parser.error(str(exc))
        return 1

    if not updated:
        print(
            f"Hata: '{args.username}' adına sahip bir kullanıcı bulunamadı.",
            file=sys.stderr,
        )
        return 1

    print(
        f"Parola başarıyla güncellendi: {args.username}",
        file=sys.stdout,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    sys.exit(main())
