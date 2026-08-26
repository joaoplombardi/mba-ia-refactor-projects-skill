"""Domain policy constants — the rules that used to be magic numbers in handlers."""

CATEGORIAS_VALIDAS = [
    "informatica",
    "moveis",
    "vestuario",
    "geral",
    "eletronicos",
    "livros",
]
CATEGORIA_PADRAO = "geral"

NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

STATUS_PEDIDO_VALIDOS = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]
STATUS_PEDIDO_PADRAO = "pendente"

TIPO_USUARIO_PADRAO = "cliente"

# Faixas de desconto sobre o faturamento bruto (limite inferior -> percentual).
# Avaliadas da maior para a menor.
FAIXAS_DESCONTO = [
    (10000, 0.10),
    (5000, 0.05),
    (1000, 0.02),
]
