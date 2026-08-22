"""Validation rules for users and login."""
import re

from config.constants import DEFAULT_ROLE, EMAIL_PATTERN, MIN_PASSWORD_LENGTH, VALID_ROLES
from errors import ValidationError


def _require_payload(payload):
    if not payload or not isinstance(payload, dict):
        raise ValidationError("Dados inválidos")
    return payload


def _email(raw):
    if not re.match(EMAIL_PATTERN, raw or ""):
        raise ValidationError("Email inválido")
    return raw


def _password(raw, short_message="Senha deve ter no mínimo 4 caracteres"):
    if not raw or len(raw) < MIN_PASSWORD_LENGTH:
        raise ValidationError(short_message)
    return raw


def _role(raw):
    if raw not in VALID_ROLES:
        raise ValidationError("Role inválido")
    return raw


def validate_create(payload):
    data = _require_payload(payload)

    if not data.get("name"):
        raise ValidationError("Nome é obrigatório")
    if not data.get("email"):
        raise ValidationError("Email é obrigatório")
    if not data.get("password"):
        raise ValidationError("Senha é obrigatória")

    return {
        "name": data["name"],
        "email": _email(data["email"]),
        "password": _password(data["password"]),
        "role": _role(data.get("role", DEFAULT_ROLE)),
    }


def validate_update(payload):
    data = _require_payload(payload)
    result = {}

    if "name" in data:
        result["name"] = data["name"]
    if "email" in data:
        result["email"] = _email(data["email"])
    if "password" in data:
        result["password"] = _password(data["password"], short_message="Senha muito curta")
    if "role" in data:
        result["role"] = _role(data["role"])
    if "active" in data:
        result["active"] = data["active"]

    return result


def validate_login(payload):
    data = _require_payload(payload)
    if not data.get("email") or not data.get("password"):
        raise ValidationError("Email e senha são obrigatórios")
    return {"email": data["email"], "password": data["password"]}
