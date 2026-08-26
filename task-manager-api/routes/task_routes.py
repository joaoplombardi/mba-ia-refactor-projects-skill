"""HTTP wiring for tasks. No ORM access, no validation, no business rules."""
from flask import Blueprint, jsonify, request

from controllers import task_controller

task_bp = Blueprint("tasks", __name__)


@task_bp.route("/tasks", methods=["GET"])
def get_tasks():
    tasks = task_controller.list_tasks()
    return jsonify([task.to_detailed_dict() for task in tasks]), 200


@task_bp.route("/tasks/search", methods=["GET"])
def search_tasks():
    tasks = task_controller.search_tasks(
        query=request.args.get("q", ""),
        status=request.args.get("status", ""),
        priority=request.args.get("priority", ""),
        user_id=request.args.get("user_id", ""),
    )
    return jsonify([task.to_dict() for task in tasks]), 200


@task_bp.route("/tasks/stats", methods=["GET"])
def task_stats():
    return jsonify(task_controller.task_stats()), 200


@task_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    task = task_controller.get_task(task_id)
    data = task.to_dict()
    data["overdue"] = task.is_overdue()
    return jsonify(data), 200


@task_bp.route("/tasks", methods=["POST"])
def create_task():
    task = task_controller.create_task(request.get_json(silent=True))
    return jsonify(task.to_dict()), 201


@task_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = task_controller.update_task(task_id, request.get_json(silent=True))
    return jsonify(task.to_dict()), 200


@task_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task_controller.delete_task(task_id)
    return jsonify({"message": "Task deletada com sucesso"}), 200
