================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.9 + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
Date:    2026-08-22

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.9
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1, sqlite3 (stdlib)
Domain:        E-commerce API — produtos, usuários, pedidos e relatório de vendas
Architecture:  Monolítica com split técnico falso — 4 arquivos nomeados por camada,
               mas persistência, regra de negócio e formatação convivem em models.py
Source files:  4 files analyzed (780 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Entry point:   app.py (Flask dev server, porta 5000)
================================
```

`models.py` não é um model: é um god module que concentra SQL, regra de negócio (cálculo de
total de pedido, faixas de desconto), validação de estoque e montagem de DTO para os 4 domínios.
`controllers.py` não orquestra: valida, chama SQL indireto e dispara "notificações" via `print`.

## Summary

CRITICAL: 8 | HIGH: 5 | MEDIUM: 5 | LOW: 4

O problema arquitetural de fundo é a ausência real de camadas: os nomes dos arquivos sugerem
MVC, mas `models.py` acumula persistência + domínio + serialização para produtos, usuários,
pedidos e relatórios. O problema de segurança mais urgente é a combinação de **SQL Injection em
todas as 21 queries** com um endpoint `/admin/query` que executa SQL arbitrário vindo do corpo
da requisição — ambos verificados como exploráveis nesta auditoria. O alvo é uma árvore MVC com
`config/`, `models/` por agregado, `controllers/`, `views/` (Blueprints) e um error handler único.

## Findings

### [CRITICAL] F01 — God Module / God Method (AP-C01)
- **File:** `models.py:1-314`, `controllers.py:1-292`
- **Description:** `models.py` contém, num único módulo sem classes, as queries SQL, as regras de
  negócio e a serialização de 4 domínios distintos: produtos (`:4-70`, `:285-314`), usuários
  (`:72-131`), pedidos (`:133-233`, `:275-283`) e relatórios (`:235-273`). `relatorio_vendas()`
  (`:235-273`) executa 5 queries, aplica a política comercial de desconto e monta o payload de
  resposta na mesma função. `controllers.py` acumula validação de entrada, orquestração e efeitos
  colaterais de notificação.
- **Impact:** Nada é testável isoladamente — testar a regra de desconto exige um banco SQLite real.
  Qualquer alteração em pedidos arrisca quebrar produtos, porque compartilham arquivo, cursor e
  conexão global. Não há costura para transação, autorização ou cache.
- **Recommendation:** Separar em `models/` por agregado (produto, usuario, pedido), mover regra de
  negócio para `controllers/` e serialização para o próprio model. Playbook §1 e §7.

### [CRITICAL] F02 — Arbitrary Query Execution Endpoint (AP-C04)
- **File:** `app.py:59-78`
- **Description:** `POST /admin/query` lê o campo `sql` do corpo da requisição e o entrega direto a
  `cursor.execute(query)` (`app.py:69`), sem autenticação, sem allowlist e sem limite de operação.
  `SELECT` retorna as linhas; qualquer outra coisa recebe `db.commit()` (`app.py:75`).
- **Impact:** **Verificado nesta auditoria.** `POST /admin/query {"sql":"SELECT nome,email,senha
  FROM usuarios"}` retornou HTTP 200 com as credenciais de todos os usuários em texto puro. O mesmo
  endpoint aceita `DROP TABLE`, `UPDATE usuarios SET tipo='admin'` e `ATTACH DATABASE` — é
  comprometimento total do banco por um chamador anônimo.
- **Recommendation:** Remover a rota. Não existe forma segura de expor execução de SQL arbitrário.
  Playbook §4.

### [CRITICAL] F03 — SQL Injection via String Concatenation (AP-C03)
- **File:** `models.py:109-111` (login), `models.py:28`, `models.py:48-50`, `models.py:58-60`,
  `models.py:68`, `models.py:92`, `models.py:126-129`, `models.py:140`, `models.py:148-151`,
  `models.py:155`, `models.py:157-161`, `models.py:163-166`, `models.py:174`, `models.py:188`,
  `models.py:192`, `models.py:220`, `models.py:224`, `models.py:279-281`, `models.py:289-297`
- **Description:** Nenhuma das 21 queries do projeto usa placeholders. Todas são montadas por
  concatenação de string com valores vindos da requisição. O caso mais grave é o login
  (`models.py:109-111`):
  `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`.
  A busca de produtos (`models.py:289-297`) concatena inclusive o termo dentro de um `LIKE '%...%'`.
- **Impact:** **Verificado nesta auditoria.** `POST /login` com
  `{"email":"' OR '1'='1","senha":"' OR '1'='1"}` retornou HTTP 200 autenticado como
  `admin@loja.com`, `tipo: admin` — bypass completo de autenticação com o payload mais básico
  que existe. `buscar_produtos` permite leitura arbitrária via `UNION SELECT`, e
  `atualizar_status_pedido` (`:279-281`) permite escrita arbitrária.
- **Recommendation:** Substituir toda concatenação por placeholders `?` com tupla de parâmetros.
  Para os filtros dinâmicos de `buscar_produtos`, montar as cláusulas em código e os valores em
  parâmetros. Playbook §3.

### [CRITICAL] F04 — Hardcoded Credentials (AP-C02)
- **File:** `app.py:7`, `controllers.py:289`, `database.py:5`
- **Description:** `SECRET_KEY` está fixa no código como `"minha-chave-super-secreta-123"`
  (`app.py:7`) e é **repetida** no corpo de resposta do `/health` (`controllers.py:289`).
  `db_path` também é literal (`database.py:5`). Nenhum valor vem do ambiente.
- **Impact:** O segredo está no histórico do git permanentemente; rotacionar exige alterar código e
  redeploy. Como a mesma chave também vaza pelo `/health` (ver F06), qualquer pessoa na internet
  consegue forjar sessões assinadas.
- **Recommendation:** Mover para `config/settings.py` lendo `os.environ`, com `.env.example` e
  default seguro apenas para desenvolvimento. Rotacionar a chave — removê-la do código não a remove
  do histórico. Playbook §2.

### [CRITICAL] F05 — Passwords Stored and Compared in Plaintext (AP-C05)
- **File:** `models.py:105-120`, `models.py:126-129`, `database.py:75-83`
- **Description:** `criar_usuario` (`:126-129`) grava a senha exatamente como recebida. `login_usuario`
  (`:109-111`) compara a senha em texto puro dentro da própria query SQL. O seed
  (`database.py:75-79`) cadastra `admin123`, `123456` e `senha123` em claro.
- **Impact:** Um vazamento do arquivo `loja.db` é imediatamente um vazamento de credenciais — não há
  nem hash, nem salt, nem função de derivação. Como usuários reutilizam senhas, o impacto extrapola
  esta aplicação.
- **Recommendation:** `werkzeug.security.generate_password_hash` / `check_password_hash` (já vem com
  Flask, sem nova dependência). Re-seed do banco de desenvolvimento. Playbook §5.

### [CRITICAL] F06 — Sensitive Data Leaked in Responses (AP-C06)
- **File:** `controllers.py:285-289`, `models.py:79-86`, `models.py:95-102`
- **Description:** `GET /health` devolve `"secret_key": "minha-chave-super-secreta-123"`,
  `"debug": true`, `"db_path"` e `"ambiente"` (`controllers.py:285-289`). `get_todos_usuarios`
  (`:79-86`) e `get_usuario_por_id` (`:95-102`) incluem o campo `senha` no dicionário serializado.
- **Impact:** **Verificado nesta auditoria.** `GET /usuarios` devolveu as senhas em claro dos 3
  usuários e `GET /health` devolveu a `SECRET_KEY`. São dois endpoints públicos, sem autenticação,
  entregando exatamente o material necessário para comprometer a aplicação.
- **Recommendation:** Lista explícita de campos públicos na serialização de usuário; `/health`
  devolve apenas status e contagens. Playbook §6.

### [CRITICAL] F07 — Unauthenticated Destructive Endpoint (AP-C07)
- **File:** `app.py:47-57`
- **Description:** `POST /admin/reset-db` executa `DELETE FROM` nas 4 tabelas sem cláusula `WHERE`,
  sem autenticação e sem confirmação. O prefixo `/admin` é decorativo — não há guard algum.
- **Impact:** Qualquer chamador anônimo apaga todo o banco com uma requisição. Combinado com o
  `DEBUG=True` exposto pelo `/health`, o alvo é trivialmente identificável.
- **Recommendation:** Remover a rota HTTP e mover a operação para um script CLI protegido por
  variável de ambiente. Playbook §4.

### [CRITICAL] F08 — Missing Transaction Boundary on Order Creation (AP-C08)
- **File:** `models.py:133-169`
- **Description:** `criar_pedido` valida o estoque num primeiro laço (`:139-146`), insere o pedido
  (`:148-151`) e, num segundo laço (`:154-166`), insere cada item e decrementa o estoque — tudo com
  um único `db.commit()` no final (`:168`) e **nenhum** `rollback`. A verificação de estoque e o
  decremento acontecem em laços separados, sem transação entre eles.
- **Impact:** Uma falha no terceiro item deixa pedido criado, dois itens gravados e estoque
  decrementado pela metade — estado permanentemente inconsistente. Duas requisições concorrentes
  passam ambas na checagem de estoque e ambas decrementam, permitindo estoque negativo (venda de
  produto inexistente).
- **Recommendation:** Envolver a operação num context manager de transação com rollback, e tornar o
  decremento condicional (`UPDATE ... WHERE id = ? AND estoque >= ?`, checando `rowcount`).
  Playbook §8.

### [HIGH] F09 — Fat Controller / Business Logic in Handlers (AP-H01)
- **File:** `controllers.py:24-62`, `controllers.py:64-96`, `controllers.py:188-220`
- **Description:** `criar_produto` (`:24-62`) tem 38 linhas de validação inline: obrigatoriedade de
  4 campos, faixas numéricas, limites de tamanho de nome e uma lista literal de categorias válidas
  (`:52`). `criar_pedido` (`:188-220`) valida, chama o model e dispara três "notificações".
- **Impact:** A regra de validação só roda dentro de um request HTTP — não há como testá-la nem
  reaproveitá-la. Foi exatamente o que aconteceu: a mesma regra foi copiada para `atualizar_produto`
  (ver F14) e já divergiu.
- **Recommendation:** Extrair um validador por entidade e um controller que orquestre. Playbook §7 e §14.

### [HIGH] F10 — Mutable Global Connection Singleton (AP-H03, AP-H04)
- **File:** `database.py:4-10`
- **Description:** `db_connection` é uma global de módulo inicializada preguiçosamente via `global`
  (`:8-10`), com `check_same_thread=False` (`:10`) para silenciar a proteção do SQLite. Toda função
  de `models.py` chama `get_db()` internamente — a dependência é oculta e não injetável.
- **Impact:** `check_same_thread=False` num servidor multi-thread compartilha um cursor entre
  requisições concorrentes: cursores são sobrescritos e as respostas podem se misturar. Nenhum model
  pode ser testado com um banco em memória sem monkey-patch do módulo.
- **Recommendation:** Classe `Database` injetada pelo composition root; models recebem a conexão no
  construtor. Playbook §9.

### [HIGH] F11 — Connection Helper with Side Effects (AP-H05)
- **File:** `database.py:7-84`
- **Description:** `get_db()` não apenas conecta: cria 4 tabelas (`:14-53`) e, se a tabela de
  produtos estiver vazia, insere 10 produtos e 3 usuários de seed (`:56-84`) — inclusive um usuário
  `admin` com senha conhecida.
- **Impact:** Obter uma conexão tem o efeito colateral de criar schema e injetar dados. Apontar a
  aplicação para um banco de produção vazio cria silenciosamente um admin com senha `admin123`.
- **Recommendation:** Separar `connect()`, `init_schema()` e `seed()`, chamados explicitamente pelo
  composition root ou por um script. Playbook §9.

### [HIGH] F12 — Side Effects Faked with print in the Controller (AP-H05, AP-L03)
- **File:** `controllers.py:208-210`, `controllers.py:247-250`
- **Description:** O fluxo de criação de pedido "envia" e-mail, SMS e push via três `print`
  (`:208-210`). A transição de status faz o mesmo (`:247-250`). Não existe camada de serviço, e a
  decisão de notificar está embutida no handler HTTP.
- **Impact:** A notificação não acontece de fato — a aplicação aparenta um comportamento que não
  tem. Quando um cliente SMTP real for plugado, ele entrará na thread do request, sem retry nem
  timeout.
- **Recommendation:** Interface `Notifier` injetada, com implementação nula em desenvolvimento;
  a decisão de notificar fica no controller. Playbook §10.

### [HIGH] F13 — Insecure Defaults Left On (AP-H07)
- **File:** `app.py:8`, `app.py:9`, `app.py:88`, `controllers.py:12` (e mais 19 handlers)
- **Description:** `DEBUG = True` na config (`:8`), `app.run(debug=True)` (`:88`) e `CORS(app)` sem
  restrição de origem (`:9`). Além disso, todo handler devolve a mensagem da exceção ao cliente:
  `return jsonify({"erro": str(e)}), 500`.
- **Impact:** O debugger do Werkzeug é execução remota de código quando alcançável. O CORS irrestrito
  permite que qualquer site faça requisições autenticadas à API. `str(e)` vaza nomes de tabela,
  caminhos de arquivo e fragmentos de SQL para o cliente.
- **Recommendation:** `DEBUG` vindo do ambiente com default `False`, CORS com allowlist de origens,
  e um error handler central que registra o erro real e devolve mensagem genérica. Playbook §2 e §12.

### [MEDIUM] F14 — Duplicated Validation Logic (AP-M02)
- **File:** `controllers.py:28-54` vs `controllers.py:72-90`
- **Description:** `criar_produto` e `atualizar_produto` reimplementam as mesmas validações. As duas
  cópias **já divergiram**: `criar_produto` valida tamanho do nome (`:47-50`) e categoria contra a
  lista de válidas (`:52-54`); `atualizar_produto` não valida nenhuma das duas.
- **Impact:** A API aceita via `PUT` um produto que rejeitaria via `POST` — nome de 1 caractere ou
  categoria inexistente entram no banco pela porta dos fundos. É um bug de correção, não só
  duplicação.
- **Recommendation:** Um `ProdutoValidator` único com `validate_create` e `validate_update`
  compartilhando as mesmas regras. Playbook §14.

### [MEDIUM] F15 — N+1 Queries in Order Listing (AP-M01)
- **File:** `models.py:171-201`, `models.py:203-233`
- **Description:** `get_pedidos_usuario` e `get_todos_pedidos` são idênticas exceto pelo filtro. Para
  cada pedido abrem um cursor e buscam os itens (`:188`, `:220`); para **cada item** abrem um
  terceiro cursor e buscam o nome do produto (`:192`, `:224`).
- **Impact:** `GET /pedidos` com 100 pedidos de 5 itens executa 1 + 100 + 500 = 601 queries. A
  latência cresce linearmente com o volume, e cada iteração cria um cursor novo sobre a conexão
  global compartilhada (F10).
- **Recommendation:** Duas queries com `IN (...)` e `LEFT JOIN produtos`, agrupando em memória.
  Unificar as duas funções numa só com filtro opcional. Playbook §13.

### [MEDIUM] F16 — Repeated Aggregation Queries (AP-M01)
- **File:** `models.py:239-254`
- **Description:** `relatorio_vendas` executa 5 queries sequenciais sobre a mesma tabela: um
  `COUNT(*)`, um `SUM(total)` e três `COUNT(*) WHERE status = '<literal>'` — um por status.
- **Impact:** 5 varreduras onde uma bastaria; adicionar um status novo exige adicionar outra query.
- **Recommendation:** Um `SELECT status, COUNT(*), SUM(total) FROM pedidos GROUP BY status`.
  Playbook §13.

### [MEDIUM] F17 — Scattered Error Handling (AP-M04)
- **File:** `controllers.py` — 20 handlers, ex. `:10-12`, `:21-22`, `:60-62`, `:95-96`, `:218-220`
- **Description:** Cada um dos 20 handlers repete o mesmo bloco `try/except Exception as e:
  return jsonify({"erro": str(e)}), 500`. Não há `@app.errorhandler` registrado em lugar nenhum.
- **Impact:** ~60 linhas duplicadas; o formato do erro varia entre handlers (alguns incluem
  `"sucesso": False`, outros não); e o `except` genérico transforma bugs de programação em 500
  silenciosos com detalhe interno vazado.
- **Recommendation:** Exceções de domínio (`ValidationError`, `NotFoundError`) mapeadas para HTTP num
  único middleware de erro. Playbook §12.

### [MEDIUM] F18 — Duplicated Manual Serialization (AP-M03)
- **File:** `models.py:12-21`, `models.py:31-40`, `models.py:304-313` (produto);
  `models.py:79-86`, `models.py:95-102` (usuário); `models.py:178-185`, `models.py:211-218` (pedido)
- **Description:** O mesmo dicionário de campos é remontado à mão em 7 lugares. Produto é serializado
  identicamente em 3 funções distintas.
- **Impact:** Adicionar um campo a produto exige editar 3 funções; esquecer uma faz endpoints
  devolverem formatos diferentes para a mesma entidade.
- **Recommendation:** Uma função de serialização por entidade, no model. Playbook §6.

### [LOW] F19 — Magic Numbers in Business Rules (AP-L01)
- **File:** `models.py:256-262`, `controllers.py:47-50`, `controllers.py:52`, `controllers.py:242`
- **Description:** A política de desconto é escrita com literais soltos: `> 10000 → 0.1`,
  `> 5000 → 0.05`, `> 1000 → 0.02` (`models.py:256-262`). Os limites de nome (`2`, `200`), a lista
  de categorias válidas (`controllers.py:52`) e a lista de status (`controllers.py:242`) também são
  literais inline. (4 ocorrências agregadas.)
- **Impact:** A regra comercial fica invisível para quem lê o código e precisa de deploy para mudar;
  as listas repetidas divergem das do banco.
- **Recommendation:** Constantes nomeadas em `config/constants.py`. Playbook §14.

### [LOW] F20 — print Used as Logging (AP-L03)
- **File:** `controllers.py:8`, `:11`, `:57`, `:61`, `:106`, `:161`, `:179`, `:182`, `:208-210`,
  `:219`, `:248`, `:250`; `app.py:56`, `:83-86`, `database.py` — 17 ocorrências agregadas
- **Description:** Eventos operacionais são registrados com `print` e concatenação de string, sem
  nível, timestamp ou destino configurável.
- **Impact:** Impossível filtrar por severidade ou desligar em produção; a saída vai para stdout sem
  estrutura. `print("Login bem-sucedido: " + email)` (`:179`) ainda registra identificador de usuário
  em log não controlado.
- **Recommendation:** `logging` da stdlib com níveis, configurado no composition root. Playbook §12.

### [LOW] F21 — String Concatenation Instead of f-strings (AP-L06)
- **File:** `controllers.py:8`, `:54`, `:57`, `:106`, `:208-210`, `:248`, `:250`;
  `models.py:143`, `:145` — 9 ocorrências agregadas
- **Description:** Mensagens montadas com `"texto " + str(x) + " mais"` em vez de f-strings, mesmo o
  projeto rodando em Python 3.9.
- **Impact:** Legibilidade; `str()` explícito espalhado esconde erros de tipo.
- **Recommendation:** f-strings. Playbook §16.

### [LOW] F22 — Inconsistent Response Contract (AP-L05)
- **File:** `controllers.py:9` vs `:20` vs `:29` vs `:58`
- **Description:** O envelope varia por endpoint: uns devolvem `{"dados": ..., "sucesso": true}`,
  outros `{"erro": ...}` sem `sucesso` (`:29`), outros `{"erro": ..., "sucesso": false}` (`:20`), e
  alguns acrescentam `"mensagem"` (`:58`).
- **Impact:** Todo cliente precisa de tratamento especial por endpoint para descobrir se a chamada
  deu certo.
- **Recommendation:** Um helper de envelope único no controller. **Preservar o shape atual de cada
  endpoint** nesta refatoração — mudar o contrato quebraria clientes. Playbook §12.

## Deprecated APIs

Varredura executada para Python/Flask (`utcnow`, `Query.get`, `before_first_request`,
`flask.json.JSONEncoder`, `werkzeug.urls`, `imp`, `distutils`, `pkg_resources`):

**No deprecated APIs detected for this stack.** O projeto usa `sqlite3` da stdlib com SQL cru e não
importa `datetime` em nenhum módulo — as timestamps vêm de `CURRENT_TIMESTAMP` no próprio SQL.
Os problemas aqui são arquiteturais e de segurança, não de obsolescência de API.

## Proposed Target Structure

```
src/
├── config/
│   ├── __init__.py
│   ├── settings.py            # env vars, sem literais de segredo
│   └── constants.py           # categorias, status, faixas de desconto
├── models/
│   ├── __init__.py
│   ├── database.py            # classe Database + transaction()
│   ├── schema.py              # init_schema() + seed() explícitos
│   ├── produto_model.py
│   ├── usuario_model.py
│   └── pedido_model.py
├── controllers/
│   ├── __init__.py
│   ├── produto_controller.py
│   ├── usuario_controller.py
│   ├── pedido_controller.py
│   ├── relatorio_controller.py
│   └── validators/
│       ├── produto_validator.py
│       └── usuario_validator.py
├── views/
│   ├── __init__.py
│   ├── produto_routes.py      # Blueprint
│   ├── usuario_routes.py
│   ├── pedido_routes.py
│   └── relatorio_routes.py
├── middlewares/
│   ├── __init__.py
│   └── error_handler.py       # registro único
├── services/
│   └── notifier.py            # interface + implementação nula
├── errors.py
└── app.py                     # create_app() — composition root
```

## Migration Risk

Mudanças de comportamento propostas, cada uma justificada por um finding:

1. **`POST /admin/query` será removida** (F02). Retorno passa de 200 para 404. Não há forma segura
   de manter execução de SQL arbitrário exposta por HTTP.
2. **`POST /admin/reset-db` será removida da API HTTP** (F07) e reimplementada como script CLI
   protegido por variável de ambiente. Retorno passa de 200 para 404.
3. **`GET /health` deixa de devolver `secret_key`, `debug`, `db_path` e `ambiente`** (F06). Os campos
   `status`, `database`, `counts` e `versao` permanecem idênticos.
4. **`GET /usuarios` e `GET /usuarios/<id>` deixam de devolver o campo `senha`** (F06).
5. **Senhas passam a ser armazenadas com hash** (F05). Os usuários de seed serão recriados com as
   mesmas senhas de desenvolvimento, então `POST /login` continua funcionando com as credenciais
   documentadas. Bancos pré-existentes exigem re-seed.
6. **`PUT /produtos/<id>` passa a validar tamanho de nome e categoria** (F14), alinhando-se ao
   `POST`. Requisições que hoje passam com dados inválidos passarão a receber 400 — é a correção do
   bug, e o comportamento fica consistente com o do `POST`.

Todos os demais endpoints mantêm path, método, status code e shape de resposta idênticos.


---

## Remediation Ledger (Fase 3)

| # | Finding | Sev. | Desfecho | Evidência / risco residual |
|---|---|---|---|---|
| F01 | God module | CRITICAL | **Fixed** | `models.py`/`controllers.py` removidos; SQL só em `src/models/` |
| F02 | Endpoint de SQL arbitrário | CRITICAL | **Fixed** | `POST /admin/query` → 404 |
| F03 | SQL Injection (21 queries) | CRITICAL | **Fixed** | login com `' OR '1'='1` → **401**; grep por SQL concatenado → vazio |
| F04 | Segredos hardcoded | CRITICAL | **Fixed** | grep por `minha-chave-super-secreta` → vazio; tudo em `os.environ` |
| F05 | Senhas em texto puro | CRITICAL | **Fixed** | PBKDF2-SHA256 com salt; login segue funcionando com as credenciais do seed |
| F06 | Dados sensíveis em resposta | CRITICAL | **Fixed** | `/health` sem `secret_key`; `/usuarios` sem `senha` |
| F07 | Reset destrutivo sem auth | CRITICAL | **Fixed** | `POST /admin/reset-db` → 404; capacidade movida para `scripts/reset_db.py` atrás de `ALLOW_DB_RESET=yes` |
| F08 | Sem transação no pedido | CRITICAL | **Fixed** | estoque intacto em 8 após falha no 2º item; decremento condicional fecha a corrida |
| F09 | Fat controller | HIGH | **Fixed** | validação em `controllers/validators/`; handlers com ≤5 linhas |
| F10 | Conexão global mutável | HIGH | **Fixed** | nenhum `global`; `Database` injetada pelo composition root |
| F11 | Efeito colateral no `get_db()` | HIGH | **Fixed** | `init_schema()` e `seed()` explícitos |
| F12 | Notificação fingida com `print` | HIGH | **Fixed** | `LoggingNotifier` injetado, nomeado pelo que é e declarando que não envia. Não decide autorização nem valor, então não precisa do gate de produção do §17. Trocar por um canal real é substituir a implementação injetada. |
| F13 | Defaults inseguros | HIGH | **Fixed** | `DEBUG` do ambiente (default `False`); CORS com allowlist; erro genérico no corpo |
| F14–F18 | Duplicação, N+1, erro espalhado | MEDIUM | **Fixed** | validators compartilhados; N+1 de 81 → 2 queries; um error handler |
| F19–F21 | Magic numbers, `print`, concatenação | LOW | **Fixed** | constantes em `config/`; `logging` com níveis; f-strings |
| F22 | Contrato de resposta inconsistente | LOW | **Deferred** | Preservado de propósito — padronizar o envelope quebraria clientes. Documentado no finding. |

**CRITICAL: 8 fixed | HIGH: 5 fixed | MEDIUM: 5 fixed | LOW: 3 fixed, 1 deferred**

Nenhum CRITICAL ou HIGH ficou sem correção.

================================
Total: 22 findings
================================
