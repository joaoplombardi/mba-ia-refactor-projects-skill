"""Persistence for the `usuarios` aggregate.

The password column is never part of a public representation — see the audit
finding on sensitive data leaked in responses.
"""

_CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")


def serialize(row):
    if row is None:
        return None
    return {campo: row[campo] for campo in _CAMPOS_PUBLICOS}


class UsuarioModel:
    def __init__(self, db):
        self.db = db

    def get_all(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT id, nome, email, tipo, criado_em FROM usuarios")
        return [serialize(row) for row in cursor.fetchall()]

    def get_by_id(self, usuario_id):
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT id, nome, email, tipo, criado_em FROM usuarios WHERE id = ?",
            (usuario_id,),
        )
        return serialize(cursor.fetchone())

    def get_by_email(self, email):
        """Returns the raw row, password hash included — for authentication only."""
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        return cursor.fetchone()

    def exists(self, usuario_id):
        cursor = self.db.cursor()
        cursor.execute("SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,))
        return cursor.fetchone() is not None

    def create(self, nome, email, senha_hash, tipo):
        with self.db.transaction() as cursor:
            cursor.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, senha_hash, tipo),
            )
            return cursor.lastrowid

    def count(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        return cursor.fetchone()[0]
