"""Single place where errors become HTTP responses.

Replaces the try/except block that was repeated in all 20 legacy handlers, each
of which returned str(e) to the client and leaked internal detail.
"""
import logging

from flask import jsonify

from src.errors import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        logger.warning("%s: %s", type(error).__name__, error.message)
        return jsonify(error.to_payload()), error.status_code

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({"erro": "Recurso não encontrado", "sucesso": False}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({"erro": "Método não permitido", "sucesso": False}), 405

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        # The real cause goes to the server log; the client gets a generic message.
        logger.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno do servidor", "sucesso": False}), 500
