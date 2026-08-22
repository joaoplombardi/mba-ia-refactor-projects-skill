"""Persistence for the `produtos` aggregate. All SQL is parameterized."""

_CAMPOS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def serialize(row):
    """Single public representation of a produto, used by every endpoint."""
    if row is None:
        return None
    return {campo: row[campo] for campo in _CAMPOS}


class ProdutoModel:
    def __init__(self, db):
        self.db = db

    def get_all(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM produtos")
        return [serialize(row) for row in cursor.fetchall()]

    def get_by_id(self, produto_id):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
        return serialize(cursor.fetchone())

    def create(self, nome, descricao, preco, estoque, categoria):
        with self.db.transaction() as cursor:
            cursor.execute(
                "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
                "VALUES (?, ?, ?, ?, ?)",
                (nome, descricao, preco, estoque, categoria),
            )
            return cursor.lastrowid

    def update(self, produto_id, nome, descricao, preco, estoque, categoria):
        with self.db.transaction() as cursor:
            cursor.execute(
                "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, "
                "estoque = ?, categoria = ? WHERE id = ?",
                (nome, descricao, preco, estoque, categoria, produto_id),
            )
            return cursor.rowcount > 0

    def delete(self, produto_id):
        with self.db.transaction() as cursor:
            cursor.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
            return cursor.rowcount > 0

    def search(self, termo=None, categoria=None, preco_min=None, preco_max=None):
        """Dynamic filters: clauses are built from code, values always bound."""
        clauses = ["1=1"]
        params = []

        if termo:
            clauses.append("(nome LIKE ? OR descricao LIKE ?)")
            params.extend([f"%{termo}%", f"%{termo}%"])
        if categoria:
            clauses.append("categoria = ?")
            params.append(categoria)
        if preco_min is not None:
            clauses.append("preco >= ?")
            params.append(preco_min)
        if preco_max is not None:
            clauses.append("preco <= ?")
            params.append(preco_max)

        cursor = self.db.cursor()
        cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params)
        return [serialize(row) for row in cursor.fetchall()]

    def count(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos")
        return cursor.fetchone()[0]

    # --- helpers used inside the order transaction ---

    def get_for_update(self, cursor, produto_id):
        cursor.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
        return cursor.fetchone()

    def decrement_stock(self, cursor, produto_id, quantidade):
        """Conditional decrement: returns False when stock is insufficient.

        Doing the check inside the UPDATE closes the race window where two
        concurrent orders both pass a separate stock check.
        """
        cursor.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
            (quantidade, produto_id, quantidade),
        )
        return cursor.rowcount > 0
