ACTION_TR = {
  "assign": "Atama",
  "edit": "Düzenleme",
  "scrap": "Hurdaya Ayırma",
  "girdi": "Girdi",
  "cikti": "Çıktı",
}

def tr_action(key: str) -> str:
    return ACTION_TR.get(key, key)

def humanize_log(row) -> str:
    """Render an inventory log entry in a human friendly format.

    The application stores log records in different shapes. Older pieces of the
    code expect Turkish field names (``tarih``, ``islem`` …) while the
    ``InventoryLog`` model uses English ones (``created_at``, ``action`` …).

    To keep templates simple, this helper tries both variants for every field
    and falls back to an empty string when a value is missing.
    """

    # Date/time of the log entry: ``tarih`` or ``created_at``
    dt_val = getattr(row, "tarih", None) or getattr(row, "created_at", None)
    if dt_val is not None:
        try:
            dt = dt_val.strftime("%d.%m.%Y %H:%M")
        except Exception:
            dt = str(dt_val)
    else:
        dt = ""

    action = tr_action(getattr(row, "islem", getattr(row, "action", "")))
    actor = getattr(row, "islem_yapan", getattr(row, "actor", ""))
    note = getattr(row, "aciklama", getattr(row, "note", ""))

    return f"{dt} - {action} - {actor} - {note}"
