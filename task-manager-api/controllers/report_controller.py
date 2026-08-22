"""Reporting use cases."""
from datetime import timedelta

from database import db
from errors import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User
from config.constants import HIGH_PRIORITY_THRESHOLD
from utils.datetime_utils import utc_now
from utils.helpers import calculate_percentage


def _counts_by(column):
    return dict(db.session.query(column, db.func.count(Task.id)).group_by(column).all())


def summary():
    status_counts = _counts_by(Task.status)
    priority_counts = _counts_by(Task.priority)

    tasks = db.session.query(Task).all()
    overdue_list = [
        {
            "id": task.id,
            "title": task.title,
            "due_date": str(task.due_date),
            "days_overdue": task.days_overdue(),
        }
        for task in tasks
        if task.is_overdue()
    ]

    seven_days_ago = utc_now() - timedelta(days=7)
    recent_tasks = db.session.query(Task).filter(Task.created_at >= seven_days_ago).count()
    recent_done = (
        db.session.query(Task)
        .filter(Task.status == "done", Task.updated_at >= seven_days_ago)
        .count()
    )

    # One grouped query for per-user totals, replacing a query per user.
    per_user_total = dict(
        db.session.query(Task.user_id, db.func.count(Task.id)).group_by(Task.user_id).all()
    )
    per_user_done = dict(
        db.session.query(Task.user_id, db.func.count(Task.id))
        .filter(Task.status == "done")
        .group_by(Task.user_id)
        .all()
    )

    user_stats = []
    for user in db.session.query(User).all():
        total = per_user_total.get(user.id, 0)
        completed = per_user_done.get(user.id, 0)
        user_stats.append(
            {
                "user_id": user.id,
                "user_name": user.name,
                "total_tasks": total,
                "completed_tasks": completed,
                "completion_rate": calculate_percentage(completed, total),
            }
        )

    return {
        "generated_at": str(utc_now()),
        "overview": {
            "total_tasks": sum(status_counts.values()),
            "total_users": db.session.query(User).count(),
            "total_categories": db.session.query(Category).count(),
        },
        "tasks_by_status": {
            "pending": status_counts.get("pending", 0),
            "in_progress": status_counts.get("in_progress", 0),
            "done": status_counts.get("done", 0),
            "cancelled": status_counts.get("cancelled", 0),
        },
        "tasks_by_priority": {
            "critical": priority_counts.get(1, 0),
            "high": priority_counts.get(2, 0),
            "medium": priority_counts.get(3, 0),
            "low": priority_counts.get(4, 0),
            "minimal": priority_counts.get(5, 0),
        },
        "overdue": {"count": len(overdue_list), "tasks": overdue_list},
        "recent_activity": {
            "tasks_created_last_7_days": recent_tasks,
            "tasks_completed_last_7_days": recent_done,
        },
        "user_productivity": user_stats,
    }


def user_report(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado")

    tasks = db.session.query(Task).filter_by(user_id=user_id).all()
    total = len(tasks)

    statistics = {
        "total_tasks": total,
        "done": sum(1 for t in tasks if t.status == "done"),
        "pending": sum(1 for t in tasks if t.status == "pending"),
        "in_progress": sum(1 for t in tasks if t.status == "in_progress"),
        "cancelled": sum(1 for t in tasks if t.status == "cancelled"),
        "overdue": sum(1 for t in tasks if t.is_overdue()),
        "high_priority": sum(1 for t in tasks if t.priority <= HIGH_PRIORITY_THRESHOLD),
    }
    statistics["completion_rate"] = calculate_percentage(statistics["done"], total)

    return {
        "user": {"id": user.id, "name": user.name, "email": user.email},
        "statistics": statistics,
    }
