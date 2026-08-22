# task-manager-api

API de Task Manager em Python/Flask, refatorada para MVC pela skill `refactor-arch`.

Este projeto já tinha separação parcial (`models/`, `routes/`, `services/`, `utils/`). A
refatoração **não achatou e reconstruiu** a estrutura: preservou o que já respeitava a regra de
dependência e introduziu a camada que faltava — `controllers/`.

## Como rodar

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

A aplicação sobe em `http://localhost:5000`. Rode `seed.py` antes do primeiro boot, senão os
endpoints devolvem listas vazias.

> **macOS:** a porta 5000 costuma estar ocupada pelo AirPlay Receiver. Use `PORT=5056 python app.py`
> ou desative o AirPlay Receiver em Ajustes do Sistema.

## Configuração

Todos os valores vêm do ambiente — veja `.env.example`. `python-dotenv` já era declarado no
`requirements.txt` mas nunca era importado; agora um `.env` local funciona direto.

| Variável | Default | Descrição |
|---|---|---|
| `SECRET_KEY` | `dev-only-insecure-key` | Chave de assinatura. Obrigatória fora de desenvolvimento. |
| `DATABASE_URI` | `sqlite:///tasks.db` | Conexão do banco. |
| `FLASK_DEBUG` | `0` | Modo debug. |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Bind do servidor. |
| `CORS_ORIGINS` | `http://localhost:3000` | Origens permitidas. |
| `EMAIL_ENABLED` | `0` | Notificações por e-mail. Desligadas por default. |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USER` / `EMAIL_PASSWORD` | — | SMTP, quando habilitado. |

## Estrutura

```
config/          settings.py (env) + constants.py (constantes que estavam mortas em helpers.py)
models/          User, Task, Category — agora com a lógica de domínio que estava duplicada nas rotas
controllers/     NOVO — casos de uso + validators/ compartilhados entre create e update
routes/          reduzidas a wiring; category_routes.py extraído de report_routes.py
middlewares/     error_handler.py — registro único
services/        notification_service.py — SMTP atrás de interface, NullEmailClient por default
utils/           helpers.py (só funções puras) + datetime_utils.py (timezone-aware)
errors.py        exceções de domínio mapeadas para HTTP
app.py           create_app() — composition root
```

## Mudanças de comportamento

Os 18 endpoints mantêm path, método e status codes. As diferenças:

- **O campo `password` não aparece mais nas respostas** de `GET /users/<id>`, `POST /users`,
  `PUT /users/<id>` e `POST /login`. Antes vazava o hash MD5, resolvido em segundos numa rainbow
  table. `GET /users` já não o devolvia — a API ficou consistente.
- **Senhas usam PBKDF2-SHA256 com salt** em vez de MD5. Os hashes antigos não são convertíveis:
  rode `python seed.py` para recriar o banco de desenvolvimento com as mesmas credenciais
  documentadas.
- **`POST /tasks` com `priority` como string não devolve mais 500.** O validador faz cast: `"3"`
  é aceito (201) e `"alta"` devolve 400 com mensagem.
- **`PUT /tasks/<id>` e `PUT /users/<id>` aplicam as mesmas validações do create.** Antes o update
  aceitava dados que o create rejeitava.
- **`generated_at` (`/reports/summary`) e `timestamp` (`/health`) passam a incluir `+00:00`.** Os
  demais timestamps não mudaram: a coluna `DateTime` do SQLite não guarda offset.
- **`marshmallow` e `requests` foram removidos do `requirements.txt`** — nunca foram importados.
