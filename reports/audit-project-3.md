================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.9 + Flask 3.0.0 + Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.0.52)
Files:   12 analyzed | ~1060 lines of code (excluindo seed.py)
Date:    2026-08-22

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.9
Framework:     Flask 3.0.0 + Flask-SQLAlchemy 3.1.1
Dependencies:  flask-cors 4.0.0, marshmallow 3.20.1, requests 2.31.0, python-dotenv 1.0.0
Domain:        Task Manager API — tasks com status/prioridade/prazo, usuários com papéis,
               categorias e relatórios de produtividade
Architecture:  Parcialmente em camadas — models/, routes/, services/ e utils/ existem, mas a
               regra de dependência é violada: routes/ acessa o ORM direto e não há controllers/
Source files:  12 files analyzed (1060 lines)
DB tables:     users, tasks, categories
Entry point:   app.py (porta 5000) — requer `python seed.py` antes do primeiro boot
================================
```

Este é o projeto mais organizado dos três, e é justamente por isso que os problemas são mais
sutis: a estrutura de diretórios *parece* MVC, mas `routes/` faz o trabalho de controller, model e
serializer ao mesmo tempo. Duas dependências declaradas — `marshmallow` (validação) e `requests` —
**nunca são importadas**: a validação foi reescrita à mão em cada rota.

## Summary

CRITICAL: 2 | HIGH: 5 | MEDIUM: 6 | LOW: 4

O problema arquitetural de fundo é a ausência da camada de controller: os 733 linhas de `routes/`
concentram validação, orquestração, queries e serialização, enquanto `models/` fica reduzido a
declaração de colunas. O problema de segurança mais urgente é o hash MD5 das senhas sendo devolvido
em texto puro nas respostas de `/users/<id>`, `POST /users`, `PUT /users` e `/login` — verificado
nesta auditoria. Este é também o projeto com maior dívida de APIs deprecadas: 39 usos de
`datetime.utcnow()` e 14 de `Query.get()`, ambos legados nas versões já instaladas.

## Findings

### [CRITICAL] F01 — Password Hash Leaked in API Responses (AP-C06)
- **File:** `models/user.py:16-25` (campo `password` em `:21`), exposto via
  `routes/user_routes.py:33` (`GET /users/<id>`), `:85` (`POST /users`), `:129` (`PUT /users/<id>`)
  e `:209` (`POST /login`)
- **Description:** `User.to_dict()` inclui `'password': self.password` (`models/user.py:21`). Todo
  endpoint que serializa um usuário com `to_dict()` devolve o hash. O `/login` (`:207-211`) devolve
  o hash da senha **junto com o token**, na resposta de autenticação.
- **Impact:** **Verificado nesta auditoria.** `GET /users/1` devolveu
  `"password":"81dc9bdb52d04dc20036dbd8313ed055"`. Esse valor é MD5 de `1234` e é resolvido
  instantaneamente em qualquer tabela rainbow pública — ou seja, o endpoint entrega a senha em
  claro na prática. Combinado com F02, um `GET /users/<id>` anônimo é suficiente para assumir
  qualquer conta.
- **Recommendation:** Lista explícita de campos públicos em `to_dict()`, sem `password`. Playbook §6.

### [CRITICAL] F02 — MD5 Used for Password Hashing (AP-C05)
- **File:** `models/user.py:27-32`
- **Description:** `set_password` usa `hashlib.md5(pwd.encode()).hexdigest()` (`:29`) e
  `check_password` recalcula o mesmo MD5 para comparar (`:32`). Sem salt, sem função de derivação de
  chave, sem fator de custo.
- **Impact:** MD5 é uma função de hash rápida e quebrada: GPUs comuns calculam bilhões por segundo,
  e a ausência de salt permite ataque por tabela precomputada contra toda a base de uma vez. O
  requisito de senha mínima de 4 caracteres (`routes/user_routes.py:64`) torna a força bruta
  instantânea. Duas contas com a mesma senha têm o mesmo hash, visível na listagem.
- **Recommendation:** `werkzeug.security.generate_password_hash` / `check_password_hash` (já
  disponível via Flask, sem nova dependência). Re-seed do banco de desenvolvimento. Playbook §5.

### [HIGH] F03 — Missing Controller Layer: Routes Do Everything (AP-H02, AP-H01)
- **File:** `routes/task_routes.py:1-299`, `routes/user_routes.py:1-211`,
  `routes/report_routes.py:1-223`
- **Description:** Os três arquivos de rota importam `db` e os models diretamente (`:2-5`) e
  executam o ORM dentro do handler. `create_task` (`task_routes.py:85-154`) tem 69 linhas cobrindo
  validação, verificação de FK, construção de entidade, commit e serialização. `update_task`
  (`:156-223`) tem 67. `summary_report` (`report_routes.py:12-101`) tem 89 linhas com 14 queries e
  a montagem do payload. Não existe diretório `controllers/`.
- **Impact:** A camada HTTP é dona do domínio: nenhuma regra é testável sem um request, e não há
  costura para transação ou autorização. `report_routes.py` ainda mistura domínios — além dos
  relatórios, é o arquivo que serve o CRUD completo de `/categories` (`:157-223`), que não tem
  relação alguma com relatórios.
- **Recommendation:** Introduzir `controllers/` entre `routes/` e `models/`; mover o CRUD de
  categorias para o seu próprio par rota/controller. Playbook §7.

### [HIGH] F04 — Anemic Models with Duplicated Domain Logic (AP-H01, AP-M02)
- **File:** `models/task.py:38-59` vs `routes/task_routes.py:30-39`, `:71-80`, `:283-287`;
  `routes/user_routes.py:171-180`; `routes/report_routes.py:33-37`, `:132-135`
- **Description:** `Task` expõe `is_overdue()` (`models/task.py:50-59`), `validate_status()`
  (`:38-43`) e `validate_priority()` (`:45-48`) — e **nenhum dos três é chamado em lugar algum**.
  A lógica de "está atrasada" foi reescrita à mão, com o mesmo aninhamento triplo de `if`, em
  **6 lugares** diferentes das rotas. A lista de status válidos aparece literal em
  `models/task.py:39`, `task_routes.py:110`, `task_routes.py:177` e `utils/helpers.py:75` e `:110`.
- **Impact:** Cinco cópias da mesma regra que já podem divergir; o model existe mas é ignorado, o
  que faz a camada de domínio ser decorativa. Mudar a definição de "atrasada" exige encontrar as
  6 cópias.
- **Recommendation:** Usar `task.is_overdue()` nos 6 pontos; centralizar `VALID_STATUSES` em
  `config/constants.py`. Playbook §14.

### [HIGH] F05 — Hardcoded Credentials and Secrets (AP-C02)
- **File:** `app.py:13`, `services/notification_service.py:7-10`
- **Description:** `SECRET_KEY = 'super-secret-key-123'` literal em `app.py:13`, junto com a URI do
  banco (`:11`). `NotificationService.__init__` fixa host, porta, usuário e senha SMTP —
  `email_password = 'senha123'` (`notification_service.py:10`). O projeto declara `python-dotenv`
  nas dependências mas **nunca o importa**: a infraestrutura para fazer certo já está instalada e
  não é usada.
- **Impact:** Segredos no histórico do git; rotação exige alterar código. A `SECRET_KEY` fixa
  permite forjar qualquer sessão assinada por Flask.
- **Recommendation:** `config/settings.py` com `os.environ` + `python-dotenv` (já em
  `requirements.txt`) e `.env.example`. Playbook §2.

### [HIGH] F06 — Side Effects and Credentials in the Service Layer (AP-H05, AP-H04)
- **File:** `services/notification_service.py:1-48`
- **Description:** `send_email` (`:12-25`) abre uma conexão SMTP síncrona, autentica e envia dentro
  da própria chamada, com credenciais fixas no construtor. As notificações são acumuladas numa lista
  de instância `self.notifications` (`:6`, `:31-36`) que serve de armazenamento. O módulo inteiro
  **não é importado por nenhuma rota** — é código morto que ainda assim carrega uma senha.
- **Impact:** Se fosse acionado, bloquearia a thread do request pelo tempo do handshake SMTP, sem
  timeout nem retry. `self.notifications` é estado em memória perdido a cada restart e não
  compartilhado entre workers. `get_notifications` (`:43-48`) varre a lista inteira em O(n).
- **Recommendation:** Interface de e-mail injetada com implementação nula em desenvolvimento;
  credenciais vindas da config; persistir notificações no banco se forem necessárias — ou remover o
  módulo, já que não é usado. Playbook §10.

### [HIGH] F07 — N+1 Queries in Listings and Reports (AP-M01)
- **File:** `routes/task_routes.py:41-57`, `routes/report_routes.py:53-68`,
  `routes/report_routes.py:157-165`, `routes/user_routes.py:22`
- **Description:** `get_tasks` (`task_routes.py:16-59`) executa, para **cada** task do laço, um
  `User.query.get()` (`:42`) e um `Category.query.get()` (`:51`). `summary_report`
  (`report_routes.py:55-68`) executa uma query de tasks por usuário dentro do laço (`:56`).
  `get_categories` (`:161-165`) faz um `COUNT` por categoria. `get_users`
  (`user_routes.py:22`) acessa `len(u.tasks)` por usuário, disparando lazy load.
- **Impact:** `GET /tasks` com 500 tasks executa 1.001 queries. `GET /reports/summary` já executa
  14 queries fixas (`:15-51`) mais uma por usuário. A latência cresce linearmente com o volume, e
  nada disso aparece em testes com o seed de 10 tasks.
- **Recommendation:** `joinedload(Task.user)` / `joinedload(Task.category)` no listing;
  `GROUP BY` para as contagens agregadas. Playbook §13.

### [MEDIUM] F08 — Deprecated APIs: datetime.utcnow() and Query.get() (AP-M07)
- **File:** 39 usos de `datetime.utcnow()` e 14 de `Query.get()` — ver tabela na seção
  *Deprecated APIs*
- **Description:** `datetime.utcnow()` é deprecado desde Python 3.12 e aparece em defaults de coluna
  (`models/task.py:15-16`, `models/user.py:14`, `models/category.py:11`) e em comparações de prazo
  (`task_routes.py:31`, `:72`, `:285`; `report_routes.py:35`, `:133`; `user_routes.py:172`).
  `Model.query.get()` é legado no SQLAlchemy 2.0 e aparece 14 vezes nas rotas.
- **Impact:** **Verificado nesta auditoria:** com SQLAlchemy 2.0.52 instalado, `User.query.get(1)`
  emite `LegacyAPIWarning`. Sobre o `utcnow`: a substituição `datetime.now(timezone.utc)` devolve um
  datetime *aware*, enquanto `utcnow()` devolve *naive* — migrar parcialmente faz
  `self.due_date < datetime.now(timezone.utc)` levantar `TypeError`. Os 39 usos precisam migrar
  juntos, incluindo os defaults de coluna e o `seed.py`.
- **Recommendation:** Migrar todos os `utcnow()` de uma vez para `datetime.now(timezone.utc)` e
  todos os `Query.get()` para `db.session.get(Model, pk)`. Playbook §15.

### [MEDIUM] F09 — Duplicated Validation, Diverging Between Create and Update (AP-M02)
- **File:** `routes/task_routes.py:96-114` vs `:166-184`; `routes/user_routes.py:61-72` vs
  `:106-122`; e `utils/helpers.py:57-108` (não utilizado)
- **Description:** As regras de título (3-200), prioridade (1-5), status e papel são escritas duas
  vezes — uma no `create`, outra no `update` — em cada arquivo de rota. Existe um
  `process_task_data()` em `utils/helpers.py:57-108` que implementa exatamente essas regras de forma
  centralizada, e **nenhuma rota o chama**. As constantes `VALID_STATUSES`, `MAX_TITLE_LENGTH`,
  `MIN_PASSWORD_LENGTH` estão declaradas em `helpers.py:110-116` e também não são usadas.
- **Impact:** As cópias já divergem: `create_task` (`:110`) valida `status` contra a lista, mas
  aceita `priority` sem cast; `update_task` (`:182`) compara `data['priority'] < 1` diretamente. A
  solução correta existe no repositório e está morta.
- **Recommendation:** Um validador por entidade, usado por create e update. Playbook §14.

### [MEDIUM] F10 — Missing Type Validation Causes 500 (AP-M06)
- **File:** `routes/task_routes.py:113`, `:182`; `routes/user_routes.py:125`
- **Description:** `priority` vem do JSON e é comparada sem cast: `if priority < 1 or priority > 5`
  (`:113`). Em Python 3, comparar `str` com `int` levanta `TypeError`. O `helpers.py:82-89` faz o
  cast corretamente — mas não é chamado.
- **Impact:** **Verificado nesta auditoria.** `POST /tasks` com `{"title":"Task String Prio",
  "priority":"3"}` devolveu **HTTP 500** com página HTML de erro do Flask, em vez de um 400 com
  mensagem. Um cliente que envia prioridade como string — comum em formulários — recebe erro de
  servidor.
- **Recommendation:** Cast explícito com tratamento de erro no validador, devolvendo 400.
  Playbook §14.

### [MEDIUM] F11 — Duplicated Manual Serialization (AP-M03)
- **File:** `routes/task_routes.py:17-28`, `:162-169`; `models/task.py:23-36`;
  `routes/user_routes.py:15-23`; `models/user.py:16-25`
- **Description:** `Task.to_dict()` existe (`models/task.py:23-36`), mas `get_tasks`
  (`task_routes.py:17-28`) remonta o dicionário campo a campo, e `get_user_tasks`
  (`user_routes.py:162-169`) monta uma **terceira** variante com subconjunto diferente de campos.
  `get_users` (`:15-23`) monta o dicionário de usuário à mão em vez de usar `User.to_dict()`.
- **Impact:** A mesma entidade tem 3 representações diferentes na mesma API. Ironicamente, é o único
  motivo pelo qual `GET /users` não vaza o hash de senha (F01) — a versão manual omite o campo
  enquanto a do model o inclui. Adicionar um campo exige editar 3 lugares.
- **Recommendation:** Uma serialização por entidade, com variantes explícitas quando necessário
  (`to_dict()` / `to_summary_dict()`). Playbook §6.

### [MEDIUM] F12 — Scattered Error Handling and Swallowed Exceptions (AP-M04, AP-M05)
- **File:** `routes/task_routes.py:62-63`, `:236-238`; `routes/user_routes.py:130-132`,
  `:149-151`; `routes/report_routes.py:186-188`, `:207-209`, `:219-221`;
  `utils/helpers.py:46-50`
- **Description:** `get_tasks` (`:13-63`) envolve o handler inteiro num `try/except:` **sem tipo de
  exceção** (`:62`) que devolve `{'error': 'Erro interno'}`. O mesmo `except:` nu aparece em mais
  6 handlers. `parse_date` (`helpers.py:44-50`) tem dois `except:` nus aninhados que devolvem
  `None` silenciosamente. Não há `@app.errorhandler` registrado em `app.py`.
- **Impact:** Um `except:` nu captura inclusive `KeyboardInterrupt` e `SystemExit`. Qualquer bug em
  `get_tasks` — um `AttributeError`, um erro de digitação — vira um 200 genérico sem rastro no log.
  Foi o que escondeu o erro de tipo do F10 em outros handlers.
- **Recommendation:** Exceções de domínio + um error handler central; `except` sempre com tipo.
  Playbook §12.

### [MEDIUM] F13 — Dead Code and Unused Dependencies (AP-M08)
- **File:** `app.py:7`; `routes/task_routes.py:7`; `routes/user_routes.py:6`;
  `models/task.py:3`; `utils/helpers.py:1-7`, `:31-34`, `:57-116`;
  `services/notification_service.py` (módulo inteiro); `requirements.txt:4-5`
- **Description:** `app.py:7` importa `os, sys, json` — nenhum é usado. `task_routes.py:7` importa
  `json, os, sys, time` — nenhum é usado. `helpers.py` importa `os, json, sys, math, hashlib`
  (`:3-7`) sem usar nenhum, e faz `import uuid` dentro da função (`:33`). `process_task_data`
  (`:57-108`), as constantes (`:110-116`) e o `NotificationService` inteiro são código morto.
  `marshmallow` e `requests` estão em `requirements.txt` e nunca são importados.
  (9 ocorrências agregadas.)
- **Impact:** O leitor não distingue o que o módulo realmente precisa. Duas dependências instaladas
  sem uso ampliam a superfície de vulnerabilidade sem benefício. Pior: a solução para o F09 e o F10
  já está escrita em `helpers.py` e ninguém percebe porque está morta.
- **Recommendation:** Remover imports não usados e dependências não utilizadas; aproveitar
  `process_task_data` como base do validador em vez de descartá-lo. Playbook §14.

### [LOW] F14 — Redundant Conditionals and Nested If Pyramids (AP-L04)
- **File:** `models/user.py:34-38`; `models/task.py:38-43`, `:50-59`;
  `routes/task_routes.py:30-39`, `:71-80`, `:141-144`, `:210-213`;
  `routes/user_routes.py:171-180` — 9 ocorrências agregadas
- **Description:** `is_admin()` (`user.py:34-38`) escreve `if self.role == 'admin': return True else:
  return False`. `is_overdue()` (`task.py:50-59`) usa três `if` aninhados com `else: return False`
  em cada nível para calcular um único booleano. `type(tags) == list` (`task_routes.py:141`,
  `:210`) em vez de `isinstance`.
- **Impact:** Legibilidade; o aninhamento triplo do `is_overdue` é justamente o que foi copiado
  errado para 6 lugares (F04) — a forma verbosa facilitou a duplicação.
- **Recommendation:** Retornar a expressão diretamente; guard clauses; `isinstance`. Playbook §16.

### [LOW] F15 — Magic Numbers and Repeated Literals (AP-L01)
- **File:** `routes/task_routes.py:96`, `:99`, `:110`, `:113`, `:177`, `:182`;
  `routes/user_routes.py:64`, `:71`, `:115`, `:120`; `routes/report_routes.py:24-28`, `:129`;
  `models/category.py:10` — 13 ocorrências agregadas
- **Description:** Limites de título (`3`, `200`), faixa de prioridade (`1`, `5`), tamanho mínimo de
  senha (`4`), `priority <= 2` como definição de "alta prioridade" (`report_routes.py:129`), a cor
  default `'#000000'` e as listas de status e papéis, todos literais inline e repetidos. As
  constantes correspondentes **existem** em `utils/helpers.py:110-116` e não são usadas (F13).
- **Impact:** Mudar o tamanho máximo de título exige encontrar 4 literais espalhados por 2 arquivos.
- **Recommendation:** Consolidar em `config/constants.py` e importar. Playbook §14.

### [LOW] F16 — print Used as Logging (AP-L03)
- **File:** `routes/task_routes.py:149`, `:153`, `:219`, `:234`; `routes/user_routes.py:83`, `:89`,
  `:147`; `services/notification_service.py:21`, `:24`; `utils/helpers.py:39`, `:41`
  — 11 ocorrências agregadas
- **Description:** Eventos operacionais registrados via `print` com f-string. `log_action`
  (`helpers.py:36-41`) é um wrapper em torno de `print` que finge ser um logger, com timestamp
  manual e sem níveis.
- **Impact:** Sem filtro por severidade, sem destino configurável, sem formato estruturado.
- **Recommendation:** `logging` da stdlib configurado no composition root. Playbook §12.

### [LOW] F17 — Insecure Defaults and Weak Password Policy (AP-H07 rebaixado para LOW)
- **File:** `app.py:34`, `app.py:15`, `routes/user_routes.py:64`, `:115`
- **Description:** `app.run(debug=True, host='0.0.0.0')` (`app.py:34`) expõe o debugger do Werkzeug
  em todas as interfaces. `CORS(app)` (`:15`) sem restrição de origem. Senha mínima de 4 caracteres
  (`user_routes.py:64`, `:115`).
- **Impact:** Classificado LOW e não HIGH porque o `debug=True` está sob o guard `__main__` e não na
  config da aplicação — em deploy WSGI real ele não é ativado. Ainda assim, `0.0.0.0` com debugger é
  execução remota de código na rede local durante o desenvolvimento, e a política de 4 caracteres
  torna o MD5 do F02 trivialmente quebrável.
- **Recommendation:** `debug` e `host` vindos da config; CORS com allowlist; mínimo de 8 caracteres.
  Playbook §2 e §12.

## Deprecated APIs

Varredura executada para Python/Flask/SQLAlchemy. Este é o projeto com maior incidência:

| API | Location | Deprecated since | Replacement |
|---|---|---|---|
| `datetime.utcnow()` | `models/task.py:15`, `:16`, `:52`; `models/user.py:14`; `models/category.py:11`; `routes/task_routes.py:31`, `:72`, `:215`, `:285`; `routes/report_routes.py:35`, `:42`, `:45`, `:71`, `:133`; `routes/user_routes.py:172`; `utils/helpers.py:38`; `services/notification_service.py:35`; `seed.py` (6×) — **39 usos** | Python 3.12 | `datetime.now(timezone.utc)` |
| `Model.query.get(pk)` | `routes/task_routes.py:42`, `:51`, `:67`, `:117`, `:122`, `:158`, `:188`, `:195`, `:227`; `routes/user_routes.py:29`, `:94`, `:136`, `:155`; `routes/report_routes.py:105`, `:192`, `:213` — **14 usos** | SQLAlchemy 2.0 (`LegacyAPIWarning` confirmado com a versão 2.0.52 instalada) | `db.session.get(Model, pk)` |
| `Model.query` (padrão legado) | usado em todos os arquivos de `routes/` | SQLAlchemy 2.0 | `db.session.execute(select(Model))` / `db.session.scalars(...)` |

**Atenção na migração (ver F08):** `datetime.utcnow()` devolve datetime *naive*;
`datetime.now(timezone.utc)` devolve *aware*. Migrar parcialmente faz as comparações de `due_date`
levantarem `TypeError`. Os 39 usos, incluindo os defaults de coluna e o `seed.py`, precisam migrar
na mesma mudança — e os dados já persistidos foram gravados como naive.

## Proposed Target Structure

Este projeto já tem separação parcial. A regra é **não achatar e reconstruir**: preservar
`models/`, `routes/` e `utils/` e introduzir a camada que falta.

```
task-manager-api/
├── config/
│   ├── settings.py            # env vars (python-dotenv já está disponível)
│   └── constants.py           # aproveita utils/helpers.py:110-116
├── models/                    # mantidos — enriquecidos com a lógica de domínio hoje duplicada
│   ├── user.py                # to_dict() sem password; hash real
│   ├── task.py                # is_overdue() passa a ser usado
│   └── category.py
├── controllers/               # NOVO — a camada que falta
│   ├── task_controller.py
│   ├── user_controller.py
│   ├── category_controller.py
│   ├── report_controller.py
│   └── validators/
│       ├── task_validator.py   # a partir de utils/helpers.py:57-108
│       └── user_validator.py
├── routes/                    # mantidos — reduzidos a wiring
│   ├── task_routes.py
│   ├── user_routes.py
│   ├── category_routes.py     # NOVO — extraído de report_routes.py:157-223
│   └── report_routes.py
├── middlewares/
│   └── error_handler.py       # registro único
├── services/
│   └── notification_service.py # credenciais na config; implementação nula por default
├── utils/helpers.py           # apenas funções puras de fato
├── errors.py
├── database.py
├── app.py                     # create_app() — composition root
└── seed.py
```

## Migration Risk

Mudanças de comportamento propostas, cada uma justificada por um finding:

1. **O campo `password` deixa de aparecer nas respostas** de `GET /users/<id>`, `POST /users`,
   `PUT /users/<id>` e `POST /login` (F01). `GET /users` já não o devolvia — a API fica consistente.
2. **Senhas passam a usar hash com salt** (F02). Os hashes MD5 existentes não são convertíveis:
   o banco de desenvolvimento será recriado via `seed.py` com as mesmas senhas documentadas, então
   `POST /login` continua funcionando com as credenciais atuais. Bancos pré-existentes exigem reset
   de senha.
3. **`POST /tasks` e `PUT /tasks/<id>` deixam de devolver 500 para `priority` como string** (F10).
   O validador faz o cast explícito, então uma string numérica (`"3"`) passa a ser aceita e devolve
   201; apenas valores realmente inválidos (`"alta"`) ou fora da faixa devolvem 400 com mensagem.
   Nenhum caso que hoje funciona deixa de funcionar — apenas o 500 desaparece.
4. **Timestamps passam a ser timezone-aware internamente** (F08). O impacto no wire é menor do que
   se poderia esperar: a coluna `db.DateTime` do SQLite não guarda offset, então `created_at`,
   `updated_at` e `due_date` continuam serializando exatamente como antes
   (`"2026-08-22 03:47:55.976971"`). Apenas os dois campos calculados no momento da requisição
   passam a carregar o sufixo `+00:00`: `generated_at` em `GET /reports/summary` e `timestamp` em
   `GET /health`. As comparações de prazo passam por `ensure_aware()`, que normaliza os valores
   naive já gravados no banco — sem isso, a migração faria `is_overdue()` levantar `TypeError`.
5. **`PUT /users/<id>` e `PUT /tasks/<id>` passam a aplicar as mesmas validações do create** (F09).
   Requisições hoje aceitas com dados inválidos passarão a receber 400.
6. **Endpoints de `/categories` mudam de blueprint** (`report_bp` → `category_bp`) (F03). Os paths,
   métodos, status codes e payloads permanecem idênticos — muda apenas a organização interna.

Os 18 endpoints mantêm path, método e status codes de sucesso idênticos.


---

## Remediation Ledger (Fase 3)

| # | Finding | Sev. | Desfecho | Evidência / risco residual |
|---|---|---|---|---|
| F01 | Hash de senha vazado em 4 endpoints | CRITICAL | **Fixed** | ocorrências de `"password"` nas respostas: 4 → **0** |
| F02 | MD5 como hash de senha | CRITICAL | **Fixed** | PBKDF2-SHA256 com salt distinto por usuário, verificado no banco |
| F03 | Camada de controller ausente | HIGH | **Fixed** | grep por `db.session`/`.query(` em `routes/` → vazio |
| F04 | Models anêmicos, lógica duplicada | HIGH | **Fixed** | `is_overdue()` passa a ser a única definição, usada nos 6 pontos |
| F05 | Segredos hardcoded | HIGH | **Fixed** | `SECRET_KEY` e SMTP vindos do ambiente; `python-dotenv` finalmente usado |
| F06 | Efeitos colaterais e credenciais no service | HIGH | **Fixed** | `NullEmailClient` por default, nomeado pelo que é e registrando supressão; SMTP real só com `EMAIL_ENABLED=1` e credenciais de config. Não decide autorização nem valor — não requer o gate do §17. |
| F07 | N+1 em listagens e relatórios | HIGH | **Fixed** | `GET /tasks`: 25 → **1** query |
| F08 | 53 APIs deprecadas | MEDIUM | **Fixed** | varredura de `utcnow()` e `Query.get()` → **0**; `ensure_aware()` normaliza linhas naive |
| F09–F12 | Validação duplicada, 500 por tipo, erro espalhado | MEDIUM | **Fixed** | `priority:"3"` → 201, `"alta"` → 400; um error handler; nenhum `except:` nu |
| F13 | Código morto e deps não usadas | MEDIUM | **Fixed** | `marshmallow` e `requests` removidos; `process_task_data` virou base dos validators |
| F14–F17 | Condicionais redundantes, literais, `print`, defaults | LOW | **Fixed** | guard clauses; constantes em `config/`; `logging`; `debug`/`host` do ambiente |

**CRITICAL: 2 fixed | HIGH: 5 fixed | MEDIUM: 6 fixed | LOW: 4 fixed**

Nenhum CRITICAL ou HIGH ficou sem correção.

================================
Total: 17 findings
================================
