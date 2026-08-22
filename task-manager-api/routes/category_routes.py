"""HTTP wiring for categories.

These endpoints used to live in report_routes.py, which owned an unrelated domain.
Paths, methods, status codes and payloads are unchanged.
"""
from flask import Blueprint, jsonify, request

from controllers import category_controller

category_bp = Blueprint("categories", __name__)


@category_bp.route("/categories", methods=["GET"])
def get_categories():
    pairs = category_controller.list_categories()
    return (
        jsonify([{**category.to_dict(), "task_count": count} for category, count in pairs]),
        200,
    )


@category_bp.route("/categories", methods=["POST"])
def create_category():
    category = category_controller.create_category(request.get_json(silent=True))
    return jsonify(category.to_dict()), 201


@category_bp.route("/categories/<int:cat_id>", methods=["PUT"])
def update_category(cat_id):
    category = category_controller.update_category(cat_id, request.get_json(silent=True))
    return jsonify(category.to_dict()), 200


@category_bp.route("/categories/<int:cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    category_controller.delete_category(cat_id)
    return jsonify({"message": "Categoria deletada"}), 200
