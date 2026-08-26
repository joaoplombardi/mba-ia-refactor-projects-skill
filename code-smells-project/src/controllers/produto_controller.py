"""Produto use cases: validate, orchestrate, return domain data."""
import logging

from src.controllers.validators import produto_validator
from src.errors import NotFoundError

logger = logging.getLogger(__name__)


class ProdutoController:
    def __init__(self, produto_model):
        self.produto_model = produto_model

    def listar(self):
        produtos = self.produto_model.get_all()
        logger.info("Listando %d produtos", len(produtos))
        return produtos

    def buscar_por_id(self, produto_id):
        produto = self.produto_model.get_by_id(produto_id)
        if produto is None:
            # This endpoint historically returned the "sucesso" flag; PUT/DELETE did not.
            raise NotFoundError("Produto não encontrado", include_sucesso=True)
        return produto

    def criar(self, payload):
        dados = produto_validator.validate_create(payload)
        produto_id = self.produto_model.create(**dados)
        logger.info("Produto criado com ID: %s", produto_id)
        return produto_id

    def atualizar(self, produto_id, payload):
        if self.produto_model.get_by_id(produto_id) is None:
            raise NotFoundError("Produto não encontrado")
        dados = produto_validator.validate_update(payload)
        self.produto_model.update(produto_id, **dados)
        return True

    def deletar(self, produto_id):
        if self.produto_model.get_by_id(produto_id) is None:
            raise NotFoundError("Produto não encontrado")
        self.produto_model.delete(produto_id)
        logger.info("Produto %s deletado", produto_id)
        return True

    def buscar(self, termo, categoria, preco_min, preco_max):
        filtros = produto_validator.validate_search_filters(
            termo, categoria, preco_min, preco_max
        )
        return self.produto_model.search(**filtros)
