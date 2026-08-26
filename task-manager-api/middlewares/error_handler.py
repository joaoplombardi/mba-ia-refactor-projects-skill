"""Single place where errors become HTTP responses.

Replaces the per-handler try/except blocks — including seven bare `except:`
clauses that turned any bug into a generic 200-shaped error with no log trace.
"""
import logging

from flask import jsonify

from errors import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        logger.warning("%s: %s", type(error).__name__, error.message)
        return jsonify(error.to_payload()), error.status_code

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({"error": "Recurso não encontrado"}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({"error": "Método não permitido"}), 405

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        logger.exception("Erro não tratado")
        return jsonify({"error": "Erro interno"}), 500
