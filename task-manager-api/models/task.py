from config.constants import CLOSED_STATUSES, DEFAULT_PRIORITY, DEFAULT_STATUS, MAX_PRIORITY, MIN_PRIORITY, VALID_STATUSES
from database import db
from utils.datetime_utils import ensure_aware, utc_now


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=DEFAULT_STATUS)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", backref="tasks")
    category = db.relationship("Category", backref="tasks")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "tags": self.tags.split(",") if self.tags else [],
        }

    def to_detailed_dict(self):
        """Listing representation: adds the derived fields the routes used to
        recompute inline, in six different places."""
        data = self.to_dict()
        data["overdue"] = self.is_overdue()
        data["user_name"] = self.user.name if self.user else None
        data["category_name"] = self.category.name if self.category else None
        return data

    def to_summary_dict(self):
        """Subset used by GET /users/<id>/tasks."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": str(self.created_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "overdue": self.is_overdue(),
        }

    @staticmethod
    def validate_status(new_status):
        return new_status in VALID_STATUSES

    @staticmethod
    def validate_priority(priority):
        return MIN_PRIORITY <= priority <= MAX_PRIORITY

    def is_overdue(self):
        """The single definition of 'overdue'. The routes had six copies of this."""
        if not self.due_date or self.status in CLOSED_STATUSES:
            return False
        return ensure_aware(self.due_date) < utc_now()

    def days_overdue(self):
        if not self.is_overdue():
            return 0
        return (utc_now() - ensure_aware(self.due_date)).days
