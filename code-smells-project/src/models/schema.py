"""Schema creation and seed data — explicit, never a side effect of connecting."""
import logging

logger = logging.getLogger(__name__)

_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        preco REAL,
        estoque INTEGER,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT,
        senha TEXT,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    )
    """,
]

_PRODUTOS_SEED = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

# Development credentials only. They are hashed on insert, never stored in clear.
_USUARIOS_SEED = [
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
]


def init_schema(db):
    with db.transaction() as cursor:
        for statement in _TABLES:
            cursor.execute(statement)
    logger.info("Schema verificado")


def seed(db, password_hasher):
    """Insert sample data only when the products table is empty."""
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] > 0:
        return False

    with db.transaction() as cursor:
        cursor.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
            "VALUES (?, ?, ?, ?, ?)",
            _PRODUTOS_SEED,
        )
        cursor.executemany(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            [
                (nome, email, password_hasher(senha), tipo)
                for nome, email, senha, tipo in _USUARIOS_SEED
            ],
        )
    logger.info("Seed aplicado: %d produtos, %d usuários", len(_PRODUTOS_SEED), len(_USUARIOS_SEED))
    return True


# Deletion order respects the foreign-key direction: children first.
_RESET_ORDER = ("itens_pedido", "pedidos", "produtos", "usuarios")


def reset(db):
    """Delete all rows. Used by scripts/reset_db.py — never exposed over HTTP."""
    with db.transaction() as cursor:
        for table in _RESET_ORDER:
            # A table name cannot be a bound parameter. This interpolation is safe
            # because `table` comes from the module-level tuple above and never
            # from user input — the only identifier interpolation in the codebase.
            cursor.execute(f"DELETE FROM {table}")  # noqa: S608
