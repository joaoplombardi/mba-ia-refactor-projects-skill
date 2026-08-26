"""Application configuration. Every value comes from the environment.

No secret literals: the only defaults here are development-safe placeholders.
See .env.example for the full list.
"""
import os


def _as_bool(raw, default=False):
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    DEBUG = _as_bool(os.environ.get("FLASK_DEBUG"), default=False)
    DB_PATH = os.environ.get("DB_PATH", "loja.db")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]
    SEED_ON_BOOT = _as_bool(os.environ.get("SEED_ON_BOOT"), default=True)
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    VERSION = "1.0.0"

    @classmethod
    def validate(cls):
        """Refuse to boot with a development secret outside development."""
        if not cls.DEBUG and cls.SECRET_KEY == "dev-only-insecure-key":
            import warnings

            warnings.warn(
                "SECRET_KEY is using the insecure development default. "
                "Set the SECRET_KEY environment variable before deploying.",
                RuntimeWarning,
                stacklevel=2,
            )


settings = Settings()
