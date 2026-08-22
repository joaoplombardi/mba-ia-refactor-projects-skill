"""Validation rules for tasks.

Built on the logic of utils/helpers.py:process_task_data, which implemented these
rules correctly and was never called — every route re-typed them by hand, and the
create/update copies had already diverged.
"""
from datetime import datetime

from config.constants import (
    DATE_FORMAT,
    DEFAULT_PRIORITY,
    DEFAULT_STATUS,
    MAX_TITLE_LENGTH,
    MIN_TITLE_LENGTH,
    MAX_PRIORITY,
    MIN_PRIORITY,
    VALID_STATUSES,
)
from errors import ValidationError


def _require_payload(payload):
    if not payload or not isinstance(payload, dict):
        raise ValidationError("Dados inválidos")
    return payload


def _title(raw):
    if not raw:
        raise ValidationError("Título é obrigatório")
    title = raw.strip() if isinstance(raw, str) else raw
    if not isinstance(title, str):
        raise ValidationError("Título inválido")
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError("Título muito curto")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError("Título muito longo")
    return title


def _status(raw):
    if raw not in VALID_STATUSES:
        raise ValidationError("Status inválido")
    return raw


def _priority(raw):
    # The legacy routes compared the raw JSON value against 1 and 5 with no cast,
    # so a string priority raised TypeError and surfaced as a 500.
    try:
        priority = int(raw)
    except (TypeError, ValueError):
        raise ValidationError("Prioridade inválida")
    if not MIN_PRIORITY <= priority <= MAX_PRIORITY:
        raise ValidationError(f"Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}")
    return priority


def _due_date(raw):
    if not raw:
        return None
    try:
        return datetime.strptime(raw, DATE_FORMAT)
    except (TypeError, ValueError):
        raise ValidationError("Formato de data inválido. Use YYYY-MM-DD")


def _tags(raw):
    if raw is None:
        return None
    if isinstance(raw, list):
        return ",".join(str(tag) for tag in raw)
    return raw


def validate_create(payload):
    data = _require_payload(payload)
    result = {
        "title": _title(data.get("title")),
        "description": data.get("description", ""),
        "status": _status(data.get("status", DEFAULT_STATUS)),
        "priority": _priority(data.get("priority", DEFAULT_PRIORITY)),
        "user_id": data.get("user_id"),
        "category_id": data.get("category_id"),
    }
    if data.get("due_date"):
        result["due_date"] = _due_date(data["due_date"])
    if data.get("tags"):
        result["tags"] = _tags(data["tags"])
    return result


def validate_update(payload):
    """Same rules as create, applied only to the keys actually present."""
    data = _require_payload(payload)
    result = {}

    if "title" in data:
        result["title"] = _title(data["title"])
    if "description" in data:
        result["description"] = data["description"]
    if "status" in data:
        result["status"] = _status(data["status"])
    if "priority" in data:
        result["priority"] = _priority(data["priority"])
    if "user_id" in data:
        result["user_id"] = data["user_id"]
    if "category_id" in data:
        result["category_id"] = data["category_id"]
    if "due_date" in data:
        result["due_date"] = _due_date(data["due_date"])
    if "tags" in data:
        result["tags"] = _tags(data["tags"])

    return result
