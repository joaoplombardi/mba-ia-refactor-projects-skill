"""Pure leaf helpers. No database access, no request access, no state.

Validation moved to controllers/validators/ (it was duplicated inline in the
routes while a correct implementation sat unused here), and the constants moved
to config/constants.py.
"""
import re

from config.constants import EMAIL_PATTERN


def format_date(date_obj):
    return str(date_obj) if date_obj else None


def calculate_percentage(part, total):
    if not total:
        return 0
    return round((part / total) * 100, 2)


def validate_email(email):
    return bool(re.match(EMAIL_PATTERN, email or ""))


def sanitize_string(value):
    return value.strip() if value else value


def is_valid_color(color):
    return bool(color) and len(color) == 7 and color[0] == "#"
