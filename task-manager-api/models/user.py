from werkzeug.security import check_password_hash, generate_password_hash

from config.constants import DEFAULT_ROLE
from database import db
from utils.datetime_utils import utc_now

# Pinned rather than left at werkzeug's default (scrypt), which needs
# hashlib.scrypt — missing from Python builds linked against older OpenSSL.
_HASH_METHOD = "pbkdf2:sha256:600000"

# Explicit allowlist: the password column is never part of a public payload.
PUBLIC_FIELDS = ("id", "name", "email", "role", "active", "created_at")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        """Public representation. Never includes the password hash."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "active": self.active,
            "created_at": str(self.created_at),
        }

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password, method=_HASH_METHOD)

    def check_password(self, raw_password):
        if not self.password:
            return False
        try:
            return check_password_hash(self.password, raw_password)
        except ValueError:
            # Legacy MD5 digest from before the migration — never a match.
            return False

    def is_admin(self):
        return self.role == "admin"
