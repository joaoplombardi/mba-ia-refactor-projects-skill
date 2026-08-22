"""Pedido use cases.

Order creation is the transaction boundary of this application: stock checks,
the order row, its items and the stock decrement either all land or none do.
"""
import logging

from src.config.constants import STATUS_PEDIDO_PADRAO
from src.controllers.validators import pedido_validator
from src.errors import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class PedidoController:
    def __init__(self, pedido_model, produto_model, usuario_model, notifier):
        self.pedido_model = pedido_model
        self.produto_model = produto_model
        self.usuario_model = usuario_model
        self.notifier = notifier

    def criar(self, payload):
        dados = pedido_validator.validate_create(payload)
        usuario_id = dados["usuario_id"]
        itens = dados["itens"]

        with self.pedido_model.db.transaction() as cursor:
            total = 0.0
            precos = {}

            for item in itens:
                produto = self.produto_model.get_for_update(cursor, item["produto_id"])
                if produto is None:
                    raise ValidationError(
                        f"Produto {item['produto_id']} não encontrado", include_sucesso=True
                    )
                if produto["estoque"] < item["quantidade"]:
                    raise ValidationError(
                        f"Estoque insuficiente para {produto['nome']}", include_sucesso=True
                    )
                precos[item["produto_id"]] = produto["preco"]
                total += produto["preco"] * item["quantidade"]

            pedido_id = self.pedido_model.create(
                cursor, usuario_id, STATUS_PEDIDO_PADRAO, total
            )

            for item in itens:
                self.pedido_model.add_item(
                    cursor,
                    pedido_id,
                    item["produto_id"],
                    item["quantidade"],
                    precos[item["produto_id"]],
                )
                # Conditional decrement: if a concurrent order consumed the stock
                # between the check above and here, this fails and the whole
                # transaction rolls back instead of driving stock negative.
                if not self.produto_model.decrement_stock(
                    cursor, item["produto_id"], item["quantidade"]
                ):
                    raise ValidationError(
                        f"Estoque insuficiente para o produto {item['produto_id']}",
                        include_sucesso=True,
                    )

        resultado = {"pedido_id": pedido_id, "total": total}
        self.notifier.pedido_criado(pedido_id, usuario_id)
        return resultado

    def listar(self, usuario_id=None):
        return self.pedido_model.list(usuario_id)

    def atualizar_status(self, pedido_id, payload):
        novo_status = pedido_validator.validate_status(payload)
        if not self.pedido_model.update_status(pedido_id, novo_status):
            raise NotFoundError("Pedido não encontrado")
        self.notifier.status_alterado(pedido_id, novo_status)
        return True
