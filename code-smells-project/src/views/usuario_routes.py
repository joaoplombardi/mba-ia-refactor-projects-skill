"""HTTP wiring for usuarios and login."""
from flask import Blueprint, jsonify, request


def create_usuario_blueprint(controller):
    bp = Blueprint("usuarios", __name__)

    @bp.route("/usuarios", methods=["GET"])
    def listar_usuarios():
        return jsonify({"dados": controller.listar(), "sucesso": True}), 200

    @bp.route("/usuarios/<int:id>", methods=["GET"])
    def buscar_usuario(id):
        return jsonify({"dados": controller.buscar_por_id(id), "sucesso": True}), 200

    @bp.route("/usuarios", methods=["POST"])
    def criar_usuario():
        usuario_id = controller.criar(request.get_json(silent=True))
        return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201

    @bp.route("/login", methods=["POST"])
    def login():
        usuario = controller.login(request.get_json(silent=True))
        return (
            jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}),
            200,
        )

    return bp
