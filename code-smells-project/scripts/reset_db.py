"""Destructive database reset.

Replaces POST /admin/reset-db, which let any anonymous caller wipe every table.
This runs only from a shell, and only with ALLOW_DB_RESET=yes set explicitly.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings  # noqa: E402
from src.models.database import Database  # noqa: E402
from src.models.schema import init_schema, reset, seed  # noqa: E402
from src.services.security import hash_password  # noqa: E402

if __name__ == "__main__":
    if os.environ.get("ALLOW_DB_RESET") != "yes":
        raise SystemExit(
            "Recusado: defina ALLOW_DB_RESET=yes para executar este script destrutivo."
        )

    db = Database(settings.DB_PATH)
    init_schema(db)
    reset(db)
    seed(db, hash_password)
    print(f"Banco {settings.DB_PATH} resetado e populado novamente.")
