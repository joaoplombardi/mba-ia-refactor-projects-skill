"""Database connection and transaction boundary.

Replaces the module-level global connection: the composition root creates one
Database and injects it into the models, so a test can hand them an in-memory
instance without patching any module.
"""
import sqlite3
from contextlib import contextmanager


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")

    @property
    def connection(self):
        return self._connection

    def cursor(self):
        return self._connection.cursor()

    @contextmanager
    def transaction(self):
        """Commit on success, roll back on any exception.

        Every multi-step write goes through here, so a failure halfway can no
        longer leave the order created and the stock half-decremented.
        """
        cursor = self._connection.cursor()
        try:
            yield cursor
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
        finally:
            cursor.close()

    def close(self):
        self._connection.close()
