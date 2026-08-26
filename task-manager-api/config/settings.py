"""Application configuration read from the environment.

python-dotenv was already declared in requirements.txt but never imported; it is
used here so a local .env works out of the box.
"""
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is declared but keep booting without it
    pass


def _as_bool(raw, default=False):
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI", "sqlite:///tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = _as_bool(os.environ.get("FLASK_DEBUG"), default=False)
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Notifications are off by default so the app never blocks on SMTP in dev.
    EMAIL_ENABLED = _as_bool(os.environ.get("EMAIL_ENABLED"), default=False)
    EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_USER = os.environ.get("EMAIL_USER", "")
    EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")

    VERSION = "1.0"

    @classmethod
    def validate(cls):
        if not cls.DEBUG and cls.SECRET_KEY == "dev-only-insecure-key":
            import warnings

            warnings.warn(
                "SECRET_KEY is using the insecure development default. "
                "Set the SECRET_KEY environment variable before deploying.",
                RuntimeWarning,
                stacklevel=2,
            )


settings = Settings()
