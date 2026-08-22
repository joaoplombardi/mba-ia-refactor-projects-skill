# code-smells-project

API de E-commerce em Python/Flask, refatorada para MVC pela skill `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente
no primeiro boot, já com produtos e usuários de exemplo.

> **macOS:** a porta 5000 costuma estar ocupada pelo AirPlay Receiver. Use `PORT=5055 python app.py`
> ou desative o AirPlay Receiver em Ajustes do Sistema.

## Configuração

Todos os valores vêm do ambiente — veja `.env.example`. Nenhum segredo está no código.

| Variável | Default | Descrição |
|---|---|---|
| `SECRET_KEY` | `dev-only-insecure-key` | Chave de assinatura. Obrigatória fora de desenvolvimento. |
| `DB_PATH` | `loja.db` | Caminho do SQLite. |
| `FLASK_DEBUG` | `0` | Modo debug. |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Bind do servidor. |
| `CORS_ORIGINS` | `http://localhost:3000` | Origens permitidas, separadas por vírgula. |
| `SEED_ON_BOOT` | `1` | Popula o banco vazio no boot. |
| `LOG_LEVEL` | `INFO` | Nível de log. |

## Estrutura

```
src/
├── config/          settings.py (env) + constants.py (regras de domínio)
├── models/          database.py, schema.py e um model por agregado — todo o SQL vive aqui
├── controllers/     casos de uso + validators/ compartilhados entre create e update
├── views/           Blueprints Flask — apenas wiring
├── middlewares/     error_handler.py — registro único
├── services/        notifier.py, security.py (hash de senha)
├── errors.py        exceções de domínio mapeadas para HTTP
└── app.py           create_app() — composition root
app.py               entry point
scripts/reset_db.py  reset destrutivo (exige ALLOW_DB_RESET=yes)
```

## Reset do banco

`POST /admin/reset-db` e `POST /admin/query` foram removidos — eram executáveis por qualquer
chamador anônimo. O reset agora é um script de shell:

```bash
ALLOW_DB_RESET=yes python scripts/reset_db.py
```

## Endpoints

Todos os endpoints originais foram preservados com path, método e status codes idênticos.
As únicas mudanças de resposta: `/health` não devolve mais `secret_key`/`debug`/`db_path`, e
`/usuarios` não devolve mais o campo `senha`.
