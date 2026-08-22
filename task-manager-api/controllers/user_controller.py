"""User use cases, including authentication."""
import logging

from sqlalchemy.orm import joinedload

from controllers.validators import user_validator
from database import db
from errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from models.task import Task
from models.user import User

logger = logging.getLogger(__name__)


def _get_or_404(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado")
    return user


def list_users():
    """Eager-loads tasks so task_count does not trigger a query per user."""
    return db.session.query(User).options(joinedload(User.tasks)).all()


def get_user(user_id):
    return _get_or_404(user_id)


def get_user_tasks(user_id):
    _get_or_404(user_id)
    return db.session.query(Task).filter_by(user_id=user_id).all()


def _assert_email_available(email, current_user_id=None):
    existing = db.session.query(User).filter_by(email=email).first()
    if existing and existing.id != current_user_id:
        raise ConflictError("Email já cadastrado")


def create_user(payload):
    data = user_validator.validate_create(payload)
    _assert_email_available(data["email"])

    user = User(name=data["name"], email=data["email"], role=data["role"])
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()
    logger.info("Usuário criado: %s - %s", user.id, user.name)
    return user


def update_user(user_id, payload):
    user = _get_or_404(user_id)
    data = user_validator.validate_update(payload)

    if "email" in data:
        _assert_email_available(data["email"], current_user_id=user_id)
        user.email = data["email"]
    if "name" in data:
        user.name = data["name"]
    if "password" in data:
        user.set_password(data["password"])
    if "role" in data:
        user.role = data["role"]
    if "active" in data:
        user.active = data["active"]

    db.session.commit()
    return user


def delete_user(user_id):
    user = _get_or_404(user_id)
    # Tasks are removed with their owner, in the same transaction.
    db.session.query(Task).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.session.delete(user)
    db.session.commit()
    logger.info("Usuário deletado: %s", user_id)


def login(payload):
    credentials = user_validator.validate_login(payload)
    user = db.session.query(User).filter_by(email=credentials["email"]).first()

    if user is None or not user.check_password(credentials["password"]):
        raise UnauthorizedError("Credenciais inválidas")
    if not user.active:
        raise ForbiddenError("Usuário inativo")

    return user
