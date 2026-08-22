"""Validation rules for pedidos."""
from src.config.constants import STATUS_PEDIDO_VALIDOS
from src.errors import ValidationError


def validate_create(dados):
    if not dados:
        raise ValidationError("Dados inválidos", include_sucesso=False)

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens or len(itens) == 0:
        raise ValidationError("Pedido deve ter pelo menos 1 item")

    normalizados = []
    for item in itens:
        if not isinstance(item, dict) or "produto_id" not in item or "quantidade" not in item:
            raise ValidationError("Item inválido: informe produto_id e quantidade")
        try:
            produto_id = int(item["produto_id"])
            quantidade = int(item["quantidade"])
        except (TypeError, ValueError):
            raise ValidationError("produto_id e quantidade devem ser numéricos")
        if quantidade <= 0:
            raise ValidationError("Quantidade deve ser maior que zero")
        normalizados.append({"produto_id": produto_id, "quantidade": quantidade})

    return {"usuario_id": usuario_id, "itens": normalizados}


def validate_status(dados):
    novo_status = (dados or {}).get("status", "")
    if novo_status not in STATUS_PEDIDO_VALIDOS:
        raise ValidationError("Status inválido")
    return novo_status
