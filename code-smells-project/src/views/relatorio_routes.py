"""HTTP wiring for reports, health check and the API index."""
from flask import Blueprint, jsonify


def create_relatorio_blueprint(relatorio_controller, health_controller, version):
    bp = Blueprint("relatorios", __name__)

    @bp.route("/relatorios/vendas", methods=["GET"])
    def relatorio_vendas():
        return jsonify({"dados": relatorio_controller.vendas(), "sucesso": True}), 200

    @bp.route("/health", methods=["GET"])
    def health_check():
        return jsonify(health_controller.check()), 200

    @bp.route("/")
    def index():
        return jsonify(
            {
                "mensagem": "Bem-vindo à API da Loja",
                "versao": version,
                "endpoints": {
                    "produtos": "/produtos",
                    "usuarios": "/usuarios",
                    "pedidos": "/pedidos",
                    "login": "/login",
                    "relatorios": "/relatorios/vendas",
                    "health": "/health",
                },
            }
        )

    return bp
