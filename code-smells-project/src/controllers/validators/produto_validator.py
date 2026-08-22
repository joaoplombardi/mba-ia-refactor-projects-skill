"""Validation rules for produtos.

Create and update now share the same rules. In the legacy code the two copies
had already diverged: update skipped the name-length and category checks, so a
PUT could write data that a POST would have rejected.
"""
from src.config.constants import (
    CATEGORIAS_VALIDAS,
    CATEGORIA_PADRAO,
    NOME_PRODUTO_MAX,
    NOME_PRODUTO_MIN,
)
from src.errors import ValidationError


def _validate(dados):
    if not dados:
        raise ValidationError("Dados inválidos")
    if "nome" not in dados:
        raise ValidationError("Nome é obrigatório")
    if "preco" not in dados:
        raise ValidationError("Preço é obrigatório")
    if "estoque" not in dados:
        raise ValidationError("Estoque é obrigatório")

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    try:
        preco = float(dados["preco"])
        estoque = int(dados["estoque"])
    except (TypeError, ValueError):
        raise ValidationError("Preço e estoque devem ser numéricos")

    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_PRODUTO_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_PRODUTO_MAX:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError(f"Categoria inválida. Válidas: {CATEGORIAS_VALIDAS}")

    return {
        "nome": nome,
        "descricao": descricao,
        "preco": preco,
        "estoque": estoque,
        "categoria": categoria,
    }


validate_create = _validate
validate_update = _validate


def validate_search_filters(termo, categoria, preco_min, preco_max):
    def _to_float(valor, campo):
        if valor in (None, ""):
            return None
        try:
            return float(valor)
        except (TypeError, ValueError):
            raise ValidationError(f"{campo} deve ser numérico")

    return {
        "termo": termo or None,
        "categoria": categoria or None,
        "preco_min": _to_float(preco_min, "preco_min"),
        "preco_max": _to_float(preco_max, "preco_max"),
    }
