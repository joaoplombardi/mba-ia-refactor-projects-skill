"""Validation rules for categories."""
from config.constants import DEFAULT_COLOR
from errors import ValidationError


def _require_payload(payload):
    if not payload or not isinstance(payload, dict):
        raise ValidationError("Dados inválidos")
    return payload


def validate_create(payload):
    data = _require_payload(payload)
    if not data.get("name"):
        raise ValidationError("Nome é obrigatório")
    return {
        "name": data["name"],
        "description": data.get("description", ""),
        "color": data.get("color", DEFAULT_COLOR),
    }


def validate_update(payload):
    data = _require_payload(payload)
    result = {}
    for field in ("name", "description", "color"):
        if field in data:
            result[field] = data[field]
    return result
