"""HTTP wiring for pedidos."""
from flask import Blueprint, jsonify, request


def create_pedido_blueprint(controller):
    bp = Blueprint("pedidos", __name__)

    @bp.route("/pedidos", methods=["POST"])
    def criar_pedido():
        resultado = controller.criar(request.get_json(silent=True))
        return (
            jsonify(
                {
                    "dados": resultado,
                    "sucesso": True,
                    "mensagem": "Pedido criado com sucesso",
                }
            ),
            201,
        )

    @bp.route("/pedidos", methods=["GET"])
    def listar_todos_pedidos():
        return jsonify({"dados": controller.listar(), "sucesso": True}), 200

    @bp.route("/pedidos/usuario/<int:usuario_id>", methods=["GET"])
    def listar_pedidos_usuario(usuario_id):
        return jsonify({"dados": controller.listar(usuario_id), "sucesso": True}), 200

    @bp.route("/pedidos/<int:pedido_id>/status", methods=["PUT"])
    def atualizar_status_pedido(pedido_id):
        controller.atualizar_status(pedido_id, request.get_json(silent=True))
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200

    return bp
