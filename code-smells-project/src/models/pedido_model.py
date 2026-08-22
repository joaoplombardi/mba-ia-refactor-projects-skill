"""Persistence for the `pedidos` aggregate.

Order listings used to run 1 + N + N*M queries. They now run two, regardless of
how many orders and items exist.
"""
from collections import defaultdict

_CAMPOS = ("id", "usuario_id", "status", "total", "criado_em")


def _serialize(row):
    return {campo: row[campo] for campo in _CAMPOS}


class PedidoModel:
    def __init__(self, db):
        self.db = db

    def list(self, usuario_id=None):
        cursor = self.db.cursor()
        if usuario_id is None:
            cursor.execute("SELECT * FROM pedidos")
        else:
            cursor.execute("SELECT * FROM pedidos WHERE usuario_id = ?", (usuario_id,))

        pedidos = [_serialize(row) for row in cursor.fetchall()]
        if not pedidos:
            return []

        for pedido in pedidos:
            pedido["itens"] = []
        por_id = {pedido["id"]: pedido for pedido in pedidos}

        # Second and last query: every item of every order, with the product name
        # resolved by a join instead of one lookup per item.
        placeholders = ",".join("?" * len(por_id))
        cursor.execute(
            f"""
            SELECT ip.pedido_id,
                   ip.produto_id,
                   ip.quantidade,
                   ip.preco_unitario,
                   COALESCE(p.nome, 'Desconhecido') AS produto_nome
              FROM itens_pedido ip
              LEFT JOIN produtos p ON p.id = ip.produto_id
             WHERE ip.pedido_id IN ({placeholders})
            """,
            list(por_id.keys()),
        )

        agrupados = defaultdict(list)
        for item in cursor.fetchall():
            agrupados[item["pedido_id"]].append(
                {
                    "produto_id": item["produto_id"],
                    "produto_nome": item["produto_nome"],
                    "quantidade": item["quantidade"],
                    "preco_unitario": item["preco_unitario"],
                }
            )

        for pedido_id, itens in agrupados.items():
            por_id[pedido_id]["itens"] = itens

        return pedidos

    def update_status(self, pedido_id, novo_status):
        with self.db.transaction() as cursor:
            cursor.execute(
                "UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id)
            )
            return cursor.rowcount > 0

    def count(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) FROM pedidos")
        return cursor.fetchone()[0]

    def sales_summary(self):
        """One grouped scan replaces the five sequential COUNT queries."""
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT status, COUNT(*) AS quantidade, COALESCE(SUM(total), 0) AS soma "
            "FROM pedidos GROUP BY status"
        )
        por_status = {}
        total_pedidos = 0
        faturamento = 0.0
        for row in cursor.fetchall():
            por_status[row["status"]] = row["quantidade"]
            total_pedidos += row["quantidade"]
            faturamento += row["soma"]
        return total_pedidos, faturamento, por_status

    # --- helpers used inside the order transaction ---

    def create(self, cursor, usuario_id, status, total):
        cursor.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, status, total),
        )
        return cursor.lastrowid

    def add_item(self, cursor, pedido_id, produto_id, quantidade, preco_unitario):
        cursor.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) "
            "VALUES (?, ?, ?, ?)",
            (pedido_id, produto_id, quantidade, preco_unitario),
        )
