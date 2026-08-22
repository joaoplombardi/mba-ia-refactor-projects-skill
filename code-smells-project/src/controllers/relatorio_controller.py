"""Sales report use case. The discount policy lives in config, not in a query."""
from src.config.constants import FAIXAS_DESCONTO


class RelatorioController:
    def __init__(self, pedido_model):
        self.pedido_model = pedido_model

    @staticmethod
    def _desconto_para(faturamento):
        for limite, percentual in FAIXAS_DESCONTO:
            if faturamento > limite:
                return faturamento * percentual
        return 0

    def vendas(self):
        total_pedidos, faturamento, por_status = self.pedido_model.sales_summary()
        desconto = self._desconto_para(faturamento)

        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": por_status.get("pendente", 0),
            "pedidos_aprovados": por_status.get("aprovado", 0),
            "pedidos_cancelados": por_status.get("cancelado", 0),
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
        }


class HealthController:
    """Health check. No longer echoes the secret key, debug flag or db path."""

    def __init__(self, produto_model, usuario_model, pedido_model, version):
        self.produto_model = produto_model
        self.usuario_model = usuario_model
        self.pedido_model = pedido_model
        self.version = version

    def check(self):
        return {
            "status": "ok",
            "database": "connected",
            "counts": {
                "produtos": self.produto_model.count(),
                "usuarios": self.usuario_model.count(),
                "pedidos": self.pedido_model.count(),
            },
            "versao": self.version,
        }
