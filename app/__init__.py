"""Expose the FastAPI application instance for ASGI servers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["app"]


def __getattr__(name: str) -> Any:  # pragma: no cover - simple delegation
    if name == "app":
        return import_module("app.main").app
    raise AttributeError(name)
