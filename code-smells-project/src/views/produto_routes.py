"""HTTP wiring for produtos. No SQL, no validation, no business rules."""
from flask import Blueprint, jsonify, request


def create_produto_blueprint(controller):
    bp = Blueprint("produtos", __name__)

    @bp.route("/produtos", methods=["GET"])
    def listar_produtos():
        return jsonify({"dados": controller.listar(), "sucesso": True}), 200

    @bp.route("/produtos/busca", methods=["GET"])
    def buscar_produtos():
        resultados = controller.buscar(
            request.args.get("q", ""),
            request.args.get("categoria"),
            request.args.get("preco_min"),
            request.args.get("preco_max"),
        )
        return (
            jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}),
            200,
        )

    @bp.route("/produtos/<int:id>", methods=["GET"])
    def buscar_produto(id):
        return jsonify({"dados": controller.buscar_por_id(id), "sucesso": True}), 200

    @bp.route("/produtos", methods=["POST"])
    def criar_produto():
        produto_id = controller.criar(request.get_json(silent=True))
        return (
            jsonify(
                {"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}
            ),
            201,
        )

    @bp.route("/produtos/<int:id>", methods=["PUT"])
    def atualizar_produto(id):
        controller.atualizar(id, request.get_json(silent=True))
        return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200

    @bp.route("/produtos/<int:id>", methods=["DELETE"])
    def deletar_produto(id):
        controller.deletar(id)
        return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200

    return bp
