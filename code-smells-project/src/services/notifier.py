"""Notification boundary.

The legacy code faked notifications with print statements inside the controller.
The decision to notify still belongs to the controller; performing it belongs
here, behind an interface the composition root can swap.
"""
import logging

logger = logging.getLogger(__name__)


class LoggingNotifier:
    """Development implementation: records the intent, sends nothing."""

    def pedido_criado(self, pedido_id, usuario_id):
        logger.info(
            "Notificação pendente: pedido %s criado para o usuário %s "
            "(canais: email, sms, push)",
            pedido_id,
            usuario_id,
        )

    def status_alterado(self, pedido_id, novo_status):
        if novo_status == "aprovado":
            logger.info("Notificação: pedido %s aprovado — preparar envio", pedido_id)
        elif novo_status == "cancelado":
            logger.info("Notificação: pedido %s cancelado — devolver estoque", pedido_id)


class NullNotifier:
    """Used in tests: does nothing at all."""

    def pedido_criado(self, pedido_id, usuario_id):
        pass

    def status_alterado(self, pedido_id, novo_status):
        pass
