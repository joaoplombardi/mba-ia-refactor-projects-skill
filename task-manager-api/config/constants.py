"""Domain policy constants.

These already existed at the bottom of utils/helpers.py and were never imported;
the same literals were re-typed inline across the route modules. This is now the
single source of truth.
"""

VALID_STATUSES = ("pending", "in_progress", "done", "cancelled")
DEFAULT_STATUS = "pending"
CLOSED_STATUSES = ("done", "cancelled")

VALID_ROLES = ("user", "admin", "manager")
DEFAULT_ROLE = "user"

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200

MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_THRESHOLD = 2

MIN_PASSWORD_LENGTH = 4

DEFAULT_COLOR = "#000000"
DATE_FORMAT = "%Y-%m-%d"

EMAIL_PATTERN = r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$"
