"""Password hashing.

Uses werkzeug's PBKDF2 implementation, which ships with Flask — no new
dependency. Replaces plaintext storage and plaintext comparison inside SQL.

The method is pinned to pbkdf2:sha256 rather than left at werkzeug's default:
the default is scrypt, which needs `hashlib.scrypt`, and that is missing from
builds compiled against older OpenSSL (including the system Python 3.9 on
macOS). PBKDF2-SHA256 is salted, iterated and available everywhere.
"""
from werkzeug.security import check_password_hash, generate_password_hash

HASH_METHOD = "pbkdf2:sha256:600000"


def hash_password(raw_password):
    return generate_password_hash(raw_password, method=HASH_METHOD)


def verify_password(stored_hash, raw_password):
    if not stored_hash:
        return False
    try:
        return check_password_hash(stored_hash, raw_password)
    except ValueError:
        # Stored value predates hashing (legacy plaintext row) — never a match.
        return False
