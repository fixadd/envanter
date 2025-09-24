"""Backwards-compatible entrypoints for database bootstrap helpers."""

from app.db.init import bootstrap_schema

__all__ = ["bootstrap_schema"]
