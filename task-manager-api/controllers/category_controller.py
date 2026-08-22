"""Category use cases.

These lived in report_routes.py, which had nothing to do with reports.
"""
import logging

from controllers.validators import category_validator
from database import db
from errors import NotFoundError
from models.category import Category
from models.task import Task

logger = logging.getLogger(__name__)


def _get_or_404(category_id):
    category = db.session.get(Category, category_id)
    if category is None:
        raise NotFoundError("Categoria não encontrada")
    return category


def list_categories():
    """Returns (category, task_count) pairs from one grouped query instead of a
    COUNT per category."""
    counts = dict(
        db.session.query(Task.category_id, db.func.count(Task.id))
        .group_by(Task.category_id)
        .all()
    )
    categories = db.session.query(Category).all()
    return [(category, counts.get(category.id, 0)) for category in categories]


def create_category(payload):
    data = category_validator.validate_create(payload)
    category = Category(**data)
    db.session.add(category)
    db.session.commit()
    logger.info("Categoria criada: %s", category.id)
    return category


def update_category(category_id, payload):
    category = _get_or_404(category_id)
    for field, value in category_validator.validate_update(payload).items():
        setattr(category, field, value)
    db.session.commit()
    return category


def delete_category(category_id):
    category = _get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    logger.info("Categoria deletada: %s", category_id)
