"""HTTP wiring for users and login."""
from flask import Blueprint, jsonify, request

from controllers import user_controller

user_bp = Blueprint("users", __name__)


@user_bp.route("/users", methods=["GET"])
def get_users():
    users = user_controller.list_users()
    return (
        jsonify(
            [{**user.to_dict(), "task_count": len(user.tasks)} for user in users]
        ),
        200,
    )


@user_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = user_controller.get_user(user_id)
    data = user.to_dict()
    data["tasks"] = [task.to_dict() for task in user.tasks]
    return jsonify(data), 200


@user_bp.route("/users", methods=["POST"])
def create_user():
    user = user_controller.create_user(request.get_json(silent=True))
    return jsonify(user.to_dict()), 201


@user_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = user_controller.update_user(user_id, request.get_json(silent=True))
    return jsonify(user.to_dict()), 200


@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user_controller.delete_user(user_id)
    return jsonify({"message": "Usuário deletado com sucesso"}), 200


@user_bp.route("/users/<int:user_id>/tasks", methods=["GET"])
def get_user_tasks(user_id):
    tasks = user_controller.get_user_tasks(user_id)
    return jsonify([task.to_summary_dict() for task in tasks]), 200


@user_bp.route("/login", methods=["POST"])
def login():
    user = user_controller.login(request.get_json(silent=True))
    return (
        jsonify(
            {
                "message": "Login realizado com sucesso",
                "user": user.to_dict(),
                "token": f"fake-jwt-token-{user.id}",
            }
        ),
        200,
    )
