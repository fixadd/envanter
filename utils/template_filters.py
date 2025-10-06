import json

from utils.i18n import humanize_log


def format_json(value):
    """Pretty-print JSON for templates.

    Accepts either a JSON string or a Python object and returns a nicely
    indented JSON representation. Falls back to ``str(value)`` if parsing
    fails so templates can render whatever was provided without breaking.
    """
    if value in (None, ""):
        return ""
    try:
        data = json.loads(value) if isinstance(value, str) else value
        return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        return str(value)


def register_filters(templates):
    """Register commonly used template filters on a Jinja2 environment."""
    templates.env.filters["humanize_log"] = humanize_log
    templates.env.filters["format_json"] = format_json
    return templates
