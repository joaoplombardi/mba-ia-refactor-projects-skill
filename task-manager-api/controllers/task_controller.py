"""Task use cases: validate, orchestrate, persist. No HTTP objects here."""
import logging

from sqlalchemy.orm import joinedload

from controllers.validators import task_validator
from database import db
from errors import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User
from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


def _get_or_404(model, entity_id, message):
    entity = db.session.get(model, entity_id)
    if entity is None:
        raise NotFoundError(message)
    return entity


def list_tasks():
    """Eager-loads user and category: one query instead of 1 + 2N."""
    return (
        db.session.query(Task)
        .options(joinedload(Task.user), joinedload(Task.category))
        .all()
    )


def get_task(task_id):
    return _get_or_404(Task, task_id, "Task não encontrada")


def _check_relations(data):
    if data.get("user_id"):
        _get_or_404(User, data["user_id"], "Usuário não encontrado")
    if data.get("category_id"):
        _get_or_404(Category, data["category_id"], "Categoria não encontrada")


def create_task(payload):
    data = task_validator.validate_create(payload)
    _check_relations(data)

    task = Task(**data)
    db.session.add(task)
    db.session.commit()
    logger.info("Task criada: %s - %s", task.id, task.title)
    return task


def update_task(task_id, payload):
    task = get_task(task_id)
    data = task_validator.validate_update(payload)
    _check_relations(data)

    for field, value in data.items():
        setattr(task, field, value)
    task.updated_at = utc_now()

    db.session.commit()
    logger.info("Task atualizada: %s", task.id)
    return task


def delete_task(task_id):
    task = get_task(task_id)
    db.session.delete(task)
    db.session.commit()
    logger.info("Task deletada: %s", task_id)


def search_tasks(query=None, status=None, priority=None, user_id=None):
    statement = db.session.query(Task)

    if query:
        statement = statement.filter(
            db.or_(Task.title.like(f"%{query}%"), Task.description.like(f"%{query}%"))
        )
    if status:
        statement = statement.filter(Task.status == status)
    if priority:
        statement = statement.filter(Task.priority == int(priority))
    if user_id:
        statement = statement.filter(Task.user_id == int(user_id))

    return statement.all()


def task_stats():
    """One grouped scan for the status counts, replacing five COUNT queries."""
    counts = dict(
        db.session.query(Task.status, db.func.count(Task.id)).group_by(Task.status).all()
    )
    total = sum(counts.values())
    done = counts.get("done", 0)

    overdue = sum(1 for task in db.session.query(Task).all() if task.is_overdue())

    return {
        "total": total,
        "pending": counts.get("pending", 0),
        "in_progress": counts.get("in_progress", 0),
        "done": done,
        "cancelled": counts.get("cancelled", 0),
        "overdue": overdue,
        "completion_rate": round((done / total) * 100, 2) if total > 0 else 0,
    }
