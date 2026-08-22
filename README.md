# Skill de Auditoria e Refatoração Arquitetural

Uma Custom Skill do Claude Code (`refactor-arch`) que audita qualquer codebase e a refatora para o
padrão MVC. A skill roda em três fases sequenciais — análise, auditoria e refatoração — e pausa
para confirmação humana antes de tocar em qualquer arquivo.

Foi construída a partir da análise manual de três projetos legados e executada nos três para provar
que é agnóstica de tecnologia: dois Python/Flask com níveis de organização diferentes e um
Node.js/Express.

| Projeto | Stack | Findings | Resultado |
|---|---|---|---|
| [code-smells-project](code-smells-project/) | Python + Flask 3.1.1 | 22 (8 CRITICAL) | MVC completo, 22/22 endpoints preservados |
| [ecommerce-api-legacy](ecommerce-api-legacy/) | Node.js + Express 4.18.2 | 18 (6 CRITICAL) | God Class dissolvida, 3/3 endpoints preservados |
| [task-manager-api](task-manager-api/) | Python + Flask 3.0 + SQLAlchemy 2.0 | 17 (2 CRITICAL) | Camada de controllers introduzida, 28/28 endpoints preservados |

Relatórios completos em [`reports/`](reports/).

---

## A) Análise Manual

Antes de escrever a skill, li os três projetos por inteiro e documentei os problemas. O que segue
é o resumo por projeto; os relatórios em `reports/` trazem os 57 findings com arquivo e linha.

### Projeto 1 — `code-smells-project` (Python/Flask, API de E-commerce)

4 arquivos, ~780 linhas. Os nomes sugerem MVC (`models.py`, `controllers.py`), mas nenhuma camada
existe de fato.

| Severidade | Problema | Local | Por que importa |
|---|---|---|---|
| CRITICAL | **SQL Injection em todas as 21 queries** | `models.py:28,48,58,68,92,109-111,126-129,140,148-151,155-166,174,188,192,220,224,279-281,289-297` | **Verifiquei explorando:** `POST /login` com `{"email":"' OR '1'='1"}` autentica como **admin**. Nenhuma query usa placeholder. |
| CRITICAL | **Endpoint de SQL arbitrário** | `app.py:59-78` | `POST /admin/query` executa qualquer SQL do corpo da requisição, sem autenticação. **Verifiquei:** dumpou as senhas de todos os usuários em texto puro. |
| CRITICAL | **Senhas em texto puro** | `models.py:105-120,126-129` | O login compara a senha em claro dentro da própria query SQL. Um vazamento do `.db` é um vazamento de credenciais. |
| CRITICAL | **Segredo vazado pelo `/health`** | `controllers.py:285-289` | O endpoint público devolve a `SECRET_KEY`, `debug` e `db_path`. `GET /usuarios` devolve o campo `senha`. |
| CRITICAL | **Sem transação na criação de pedido** | `models.py:133-169` | Valida estoque num laço e decrementa em outro, com um único commit e nenhum rollback. Falha no meio deixa pedido criado e estoque pela metade; concorrência permite estoque negativo. |
| HIGH | **God module** | `models.py:1-314` | Um módulo com SQL, regra de negócio e serialização para 4 domínios. Testar a regra de desconto exige um SQLite real. |
| HIGH | **Conexão global mutável** | `database.py:4-10` | `global db_connection` com `check_same_thread=False`, e `get_db()` ainda cria schema e injeta seeds como efeito colateral. |
| MEDIUM | **Validação duplicada e já divergente** | `controllers.py:28-54` vs `:72-90` | `POST` valida tamanho de nome e categoria; `PUT` não. A API aceita via update o que rejeita via create — é bug, não só duplicação. |
| MEDIUM | **N+1 em listagem de pedidos** | `models.py:171-201`, `:203-233` | 100 pedidos de 5 itens = 601 queries. |
| LOW | **Magic numbers na política comercial** | `models.py:256-262` | Faixas de desconto (`>10000 → 0.1`) como literais soltos. |
| LOW | **`print` como log** | 17 ocorrências | Sem nível, sem timestamp; inclui `print("Login bem-sucedido: " + email)`. |

### Projeto 2 — `ecommerce-api-legacy` (Node.js/Express, LMS com checkout)

3 arquivos, ~180 linhas — a maior densidade de problema por linha dos três.

| Severidade | Problema | Local | Por que importa |
|---|---|---|---|
| CRITICAL | **God Class** | `AppManager.js:4-141` | Uma classe abre o banco, cria schema, registra rotas, aprova pagamento e monta respostas. O `const self = this` (`:26`) existe porque o `this` se perde nas callbacks aninhadas. |
| CRITICAL | **Chave `pk_live_` e senha de produção hardcoded** | `utils.js:1-7` | Chave de gateway de pagamento em ambiente vivo, commitada. O arquivo se chama `utils.js` — o nome esconde que ali estão os segredos. |
| CRITICAL | **Cartão e chave logados em texto puro** | `AppManager.js:45` | **Verifiquei:** o log gravou `Processando cartão 4111222233334444 na chave pk_live_...`. Violação direta de PCI-DSS. |
| CRITICAL | **Criptografia falsa** | `utils.js:17-23` | `badCrypto()` repete 10.000× os 2 primeiros caracteres do base64 da senha e trunca em 10. Sem salt, entropia quase nula, 10.000 iterações de CPU desperdiçada. |
| CRITICAL | **Pagamento aprovado por string do cliente** | `AppManager.js:46` | `cc.startsWith("4") ? "PAID" : "DENIED"`. Enviar `"card": "4"` matricula em qualquer curso e registra receita inexistente. |
| CRITICAL | **Sem transação; linhas órfãs** | `AppManager.js:50-63`, `:131-137` | **Verifiquei:** após `DELETE /api/users/1`, o relatório passou a mostrar `{"student":"Unknown","paid":997}`. A própria resposta admite: *"as matrículas e pagamentos ficaram sujos no banco"*. |
| HIGH | **Pirâmide de callbacks e orquestração manual** | `AppManager.js:37-77`, `:80-129` | **Verifiquei:** duas chamadas idênticas ao relatório financeiro devolveram os cursos em **ordens diferentes**. Contadores `pending--` decrementados dentro de `forEach` assíncrono, com resposta enviada de 3 lugares e 4 `err` ignorados. |
| HIGH | **Cache global sem limite** | `utils.js:9-15` | `globalCache` cresce uma entrada por checkout, para sempre. `totalRevenue` é exportado por valor — sempre `0` para quem importa. |
| MEDIUM | **Validação ausente** | `AppManager.js:29-35` | Só checa presença. `card` numérico faz `cc.startsWith` lançar `TypeError` dentro de callback assíncrono — o que **derruba o processo Node inteiro**. |
| MEDIUM | **API legada** | `AppManager.js:1` | `sqlite3.verbose()` incondicional em produção; acesso a banco 100% callback-only rodando em Node 26. |
| LOW | **Nomes de uma letra** | `AppManager.js:29-33` | `u`, `e`, `p`, `cid`, `cc`. `e` é e-mail — mas `e` é a convenção universal para `error` em JS. |
| LOW | **Contrato de resposta inconsistente** | `:35,60,98,135` | Sucessos ora JSON, ora texto puro; erros sempre texto puro. |

### Projeto 3 — `task-manager-api` (Python/Flask, Task Manager)

12 arquivos, ~1060 linhas. O mais organizado dos três — e por isso com os problemas mais sutis.

| Severidade | Problema | Local | Por que importa |
|---|---|---|---|
| CRITICAL | **Hash de senha vazado nas respostas** | `models/user.py:21` → 4 endpoints | **Verifiquei:** `GET /users/1` devolve `"password":"81dc9bdb52d04dc20036dbd8313ed055"` — MD5 de `1234`, resolvido instantaneamente em rainbow table. O `/login` devolve o hash junto com o token. |
| CRITICAL | **MD5 como hash de senha** | `models/user.py:27-32` | Rápido, sem salt, quebrado. Com a política de senha mínima de 4 caracteres (`user_routes.py:64`), a força bruta é instantânea. |
| HIGH | **Camada de controller ausente** | `routes/*.py` (733 linhas) | As rotas importam o ORM direto. `create_task` tem 69 linhas, `summary_report` tem 89 com 14 queries. `report_routes.py` ainda serve o CRUD de `/categories`, que não tem relação com relatórios. |
| HIGH | **Models anêmicos com lógica duplicada** | `models/task.py:38-59` vs 6 pontos nas rotas | `is_overdue()`, `validate_status()` e `validate_priority()` existem no model e **nenhum é chamado**. A regra "está atrasada" foi reescrita à mão em 6 lugares. |
| HIGH | **N+1 em listagens e relatórios** | `task_routes.py:41-57`, `report_routes.py:55-68` | `GET /tasks` com 500 tasks = 1.001 queries. Invisível no seed de 10 tasks. |
| MEDIUM | **APIs deprecadas** | 39× `datetime.utcnow()`, 14× `Query.get()` | **Verifiquei:** com SQLAlchemy 2.0.52 instalado, `User.query.get(1)` emite `LegacyAPIWarning`. Migrar `utcnow` pela metade quebra as comparações de prazo com `TypeError` (naive vs aware). |
| MEDIUM | **Validação de tipo ausente causa 500** | `task_routes.py:113` | **Verifiquei:** `POST /tasks` com `"priority":"3"` devolve **HTTP 500** com página HTML — comparar `str` com `int` lança `TypeError`. |
| MEDIUM | **Código morto que já resolvia o problema** | `utils/helpers.py:57-116` | `process_task_data()` implementa a validação corretamente, com o cast que falta, e nunca é chamado. As constantes (`VALID_STATUSES`, `MAX_TITLE_LENGTH`) também estão lá, mortas. `marshmallow` e `requests` estão no `requirements.txt` sem nenhum import. |
| LOW | **Condicionais redundantes** | `models/user.py:34-38` | `if role == 'admin': return True else: return False`. O `is_overdue` usa 3 `if` aninhados — a forma verbosa foi justamente o que facilitou copiá-lo errado 6 vezes. |
| LOW | **Literais repetidos** | 13 ocorrências | Limites de título, faixa de prioridade e listas de status inline, enquanto as constantes existem mortas em `helpers.py`. |

---

## B) Construção da Skill

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                              # o prompt: 3 fases, regras inegociáveis, tratamento de falha
└── references/
    ├── project-analysis.md               # heurísticas de detecção (Fase 1)
    ├── antipattern-catalog.md            # 28 anti-patterns com sinais de detecção (Fase 2)
    ├── report-template.md                # formato do relatório (Fase 2)
    ├── architecture-guidelines.md        # MVC alvo e regra de dependência (Fase 3)
    └── refactoring-playbook.md           # 16 transformações com antes/depois (Fase 3)
```

O `SKILL.md` é curto e instrui *o que fazer*; os arquivos de referência carregam o conhecimento de
domínio e são lidos sob demanda — a tabela no `SKILL.md` diz qual arquivo abrir em qual fase, para
não gastar contexto lendo os cinco de uma vez.

### Decisões de design

**Sinais de detecção acionáveis, não adjetivos.** Cada anti-pattern do catálogo traz o que procurar
concretamente. Não "código acoplado", mas `"SELECT .*" *\+` ou `let pending = xs.length; pending--`.
O catálogo é explícito: um hit de grep é *candidato*, não finding — é preciso ler o código em volta
para confirmar. Foi o que evitou falsos positivos, por exemplo com `Buffer.from()` no Projeto 2, que
parece o `new Buffer()` deprecado mas já é a forma correta.

**Regras de escalonamento de severidade.** A tabela de severidade sozinha produz classificações
inconsistentes em casos de fronteira. Adicionei três regras que a sobrescrevem: +1 quando o código
lida com autenticação, pagamento ou dado pessoal; duplicação sobe para HIGH quando o que se duplica
é uma *regra de validação* (porque a divergência vira bug de correção — exatamente o que aconteceu
no Projeto 1); e LOW repetido mais de ~10 vezes vira um único finding agregado em MEDIUM, para o
relatório não afogar os problemas graves em ruído de nomenclatura.

**Anti-patterns escolhidos.** 28 no total, cobrindo as três categorias que encontrei na análise
manual: segurança (SQLi, segredos, hash quebrado, vazamento em resposta, endpoint destrutivo),
arquitetura (God Class, fat controller, ausência de camada, estado global, sem injeção) e
qualidade (N+1, duplicação, erro espalhado, API deprecada, magic numbers). Incluí `AP-C08 —
Missing Transaction Boundary` como CRITICAL depois de ver os três projetos falharem nele de formas
diferentes: no Projeto 1 deixa estoque inconsistente, no 2 deixa órfãos que corrompem o relatório
financeiro, e no 3 o delete de usuário só funciona porque apaga as tasks manualmente antes.

**Preservação de comportamento como contrato.** A regra mais importante do `SKILL.md`: toda rota,
método, status code e shape de resposta que existia antes precisa existir depois. A Fase 3 começa
capturando o inventário de rotas **do código antigo** — nunca do novo, que é onde um agente
naturalmente erraria — e valida contra ele. Mudanças de comportamento são permitidas apenas quando
justificadas por um finding de segurança, e precisam ser listadas explicitamente em
"Behaviour changes".

**Como garanti que é agnóstica de tecnologia.** Três mecanismos:

1. *Detecção por manifesto, não por suposição.* A Fase 1 lê `requirements.txt` / `package.json` /
   `go.mod` e confirma com um import no código. A versão vem do manifesto, não de um chute.
2. *Sinais por stack, com instrução de reportar só o que existe.* A varredura de APIs deprecadas
   tem tabelas separadas para Python e Node. No Projeto 1 o resultado honesto foi "nenhuma
   encontrada" — e o relatório diz isso, em vez de inventar.
3. *Camadas canônicas, idiomas locais.* O `architecture-guidelines.md` fixa as fronteiras (models
   não conhecem HTTP, rotas não conhecem SQL) mas manda usar a primitiva do próprio framework:
   Blueprint no Flask, Router no Express. O playbook alterna exemplos em Python e JavaScript de
   propósito, para a *forma* da transformação ficar clara independentemente da sintaxe.

### Desafios encontrados

**O contrato de erro do Projeto 1 é inconsistente — e preservá-lo exigiu desenho.** Alguns erros
devolvem `{"erro": "..."}`, outros `{"erro": "...", "sucesso": false}`. Pior: `GET /produtos/<id>`
inexistente devolve com a flag, mas `PUT` e `DELETE` do mesmo recurso devolvem sem. Centralizar o
tratamento de erro sem quebrar clientes exigiu um parâmetro `include_sucesso` na classe de erro, com
cada ponto de raise decidindo. Documentei a inconsistência como finding LOW e **não** a corrigi —
padronizar seria uma mudança de contrato que o usuário não pediu.

**Migração parcial de `datetime.utcnow()` quebra a aplicação.** No Projeto 3, `utcnow()` devolve
datetime *naive* e o substituto devolve *aware*; comparar os dois lança `TypeError`. Migrar só as
comparações e esquecer os defaults de coluna — o caminho natural de um grep-and-replace — derruba o
`is_overdue()`. Foram 39 usos que precisaram migrar juntos, incluindo o `seed.py`, mais uma função
`ensure_aware()` para normalizar as linhas já gravadas no formato naive. Registrei isso como um
aviso explícito no playbook §15.

**`hashlib.scrypt` não existe em todo lugar.** O default do `generate_password_hash` do Werkzeug é
scrypt, que exige `hashlib.scrypt` — ausente em builds do Python linkados contra OpenSSL antigo,
incluindo o Python 3.9 do sistema no macOS. O boot falhou na primeira tentativa. A correção foi
fixar `pbkdf2:sha256` explicitamente, com o motivo documentado no código.

**Portas ocupadas mascaram falhas de validação.** A porta 5000 no macOS é do AirPlay Receiver, que
responde **403 a tudo** — o que parece a aplicação rejeitando requisições, não a aplicação ausente.
A porta 3000 estava tomada por um túnel SSH em IPv4 enquanto o Node subia em IPv6, produzindo
"empty reply from server". Nos dois casos o servidor real nunca subiu. Por isso o `SKILL.md` manda
capturar o baseline **com o app efetivamente rodando** e nunca reportar endpoint funcionando sem
tê-lo chamado — e a configuração de porta virou variável de ambiente nos três projetos.

---

## C) Resultados

### Antes / Depois

| | Projeto 1 | Projeto 2 | Projeto 3 |
|---|---|---|---|
| **Arquivos** | 4 → 33 | 3 → 21 | 12 → 32 |
| **Linhas** | 780 → 1.266 | 180 → 815 | 1.060 → 1.273 |
| **Camadas** | nenhuma real | God Class | parcial, sem controllers |
| **SQL Injection** | 21 queries → **0** | já parametrizado | ORM |
| **Segredos no código** | 3 → **0** | 4 → **0** | 2 → **0** |
| **Hash de senha** | texto puro → PBKDF2 | `badCrypto()` → scrypt | MD5 → PBKDF2 |
| **Credenciais em resposta** | 2 endpoints → **0** | cartão em log → mascarado | 4 endpoints → **0** |
| **Transações** | nenhuma → em toda escrita múltipla | nenhuma → checkout e delete | commit único → delete atômico |
| **Tratamento de erro** | 20 blocos duplicados → **1** | 7 blocos + 4 erros ignorados → **1** | 7 `except:` nus → **1** |
| **APIs deprecadas** | 0 | 2 → **0** | 53 → **0** |
| **Queries (endpoint de listagem)** | 81 → **2** | 1+N+2N → **2** | 25 → **1** |

O aumento de linhas é esperado e desejado: as camadas explícitas, os validators compartilhados e os
docstrings que registram *por que* cada transformação aconteceu ocupam espaço que o código
espremido não ocupava.

### Checklist de validação

**Fase 1 — Análise** (3/3 projetos)

- [x] Linguagem detectada corretamente — Python 3.9, JavaScript/Node, Python 3.9
- [x] Framework detectado corretamente — Flask 3.1.1, Express 4.18.2, Flask 3.0.0 + SQLAlchemy 2.0.52
- [x] Domínio descrito corretamente — E-commerce, LMS com checkout, Task Manager
- [x] Número de arquivos condiz — 4, 3, 12

**Fase 2 — Auditoria** (3/3 projetos)

- [x] Relatório segue o template de `report-template.md`
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados CRITICAL → LOW
- [x] Mínimo de 5 findings — **22, 18 e 17**
- [x] Detecção de APIs deprecated incluída — 0 no P1 (reportado honestamente), 2 no P2, 53 no P3
- [x] Skill pausou e pediu confirmação antes da Fase 3

**Fase 3 — Refatoração** (3/3 projetos)

- [x] Estrutura de diretórios segue MVC
- [x] Configuração extraída para módulo de config, sem hardcoded
- [x] Models abstraem dados — todo o SQL vive neles
- [x] Views/Routes separadas — zero acesso a ORM/SQL
- [x] Controllers concentram o fluxo
- [x] Error handling centralizado — um registro por aplicação
- [x] Entry point claro — composition root explícito
- [x] Aplicação inicia sem erros
- [x] Endpoints originais respondem corretamente

### Logs de validação

**Projeto 1** — 22 endpoints, diff de status codes contra o baseline:

```
✓ TODOS OS STATUS CODES IDÊNTICOS AO BASELINE
```

Diferenças de corpo: apenas as duas remoções intencionais (`secret_key`/`debug`/`db_path` do
`/health`, campo `senha` de `/usuarios`) e os timestamps do banco recriado.

Sondas de regressão de segurança:

```
### SQLi login bypass (antes: 200 como admin):
{"erro":"Email ou senha inválidos","sucesso":false}   [401]
### /admin/query (antes: 200 dumpando senhas):
{"erro":"Recurso não encontrado","sucesso":false}     [404]
### /admin/reset-db (antes: 200 apagando tudo):
{"erro":"Recurso não encontrado","sucesso":false}     [404]
### Estoque insuficiente (rollback):
{"erro":"Estoque insuficiente para Notebook Gamer"}   [400]
### Estoque da cadeira (id 6) deve continuar 8:
estoque = 8                                            ← rollback confirmado, sem decremento parcial
```

N+1: `20 pedidos, 60 itens -> 2 queries` (o legado executaria 81).

**Projeto 2** — 8 chamadas, status codes idênticos ao baseline. Determinismo do relatório:

```
=== 6 chamadas consecutivas ===
   ['Clean Architecture', 'Docker']
   ['Clean Architecture', 'Docker']
   ['Clean Architecture', 'Docker']
   ['Clean Architecture', 'Docker']
   ['Clean Architecture', 'Docker']
   ['Clean Architecture', 'Docker']
```

(No baseline, duas chamadas idênticas já devolviam ordens diferentes.)

```
=== Órfãos após DELETE (antes: student:Unknown) ===
  ✓ zero órfãos
=== card numérico (antes: derrubava o processo) ===
Bad Request   [400]
  ✓ servidor continua respondendo
=== rollback transacional ===
  erro esperado: falha simulada do gateway de persistência
  matrículas: 1 -> 1
  usuários:   1 -> 1
  ✓ rollback completo — nenhum estado parcial
```

Log do servidor, com cartão mascarado e sem a chave do gateway:

```
INFO  Processando pagamento de 497 no cartão ****4444
INFO  Checkout concluído: matrícula 2 no curso Docker
WARN  PaymentDeniedError: Pagamento recusado
```

**Projeto 3** — 28 endpoints, única diferença de status code contra o baseline:

```
20c20
< [500]      ← POST /tasks com "priority":"3"
---
> [201]      ← agora o validador faz cast; "alta" devolve 400 com mensagem
```

```
vazamentos de password: 0        (baseline: 4)
APIs deprecadas restantes: 0     (baseline: 53)
N+1: 12 tasks serializadas -> 1 query   (o legado executaria 25)
```

Hashes com salt distinto por usuário:

```
joao@email.com:  pbkdf2:sha256:600000$KLAd7TMDrwGc90HW$...
maria@email.com: pbkdf2:sha256:600000$XLgWW07CqhUirXhm$...
pedro@email.com: pbkdf2:sha256:600000$gih3AA4faI5FT1sj$...
```

### Ação pendente para quem herdar estes repositórios

Os segredos removidos do código **continuam no histórico do git**. Precisam ser rotacionados, não
apenas apagados: a `SECRET_KEY` do Projeto 1, a chave `pk_live_...` do gateway de pagamento e a
senha do banco no Projeto 2, e a `SECRET_KEY` e senha SMTP do Projeto 3.

---

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview)
- Python 3.9+ (projetos 1 e 3)
- Node.js 18+ (projeto 2)

### Rodar a skill

A skill já está em `.claude/skills/refactor-arch/` dentro dos três projetos. Entre no diretório do
projeto e invoque:

```bash
cd code-smells-project
claude "/refactor-arch"
```

```bash
cd ecommerce-api-legacy
claude "/refactor-arch"
```

```bash
cd task-manager-api
claude "/refactor-arch"
```

A skill imprime a análise (Fase 1), o relatório de auditoria (Fase 2) e **pausa** pedindo
`Proceed with refactoring (Phase 3)? [y/n]`. Nada é modificado até você responder `y`.

Para aplicar a skill a um projeto novo, copie a pasta:

```bash
cp -R code-smells-project/.claude/skills/refactor-arch /caminho/do/projeto/.claude/skills/
```

### Validar que a refatoração funciona

**Projeto 1:**

```bash
cd code-smells-project && pip install -r requirements.txt && PORT=5055 python app.py
```

```bash
curl -s localhost:5055/produtos | head -c 200 && curl -s -X POST localhost:5055/login -H 'Content-Type: application/json' -d '{"email":"joao@email.com","senha":"123456"}'
```

O login por injeção deve falhar com 401:

```bash
curl -s -X POST localhost:5055/login -H 'Content-Type: application/json' -d '{"email":"'"'"' OR '"'"'1'"'"'='"'"'1","senha":"x"}'
```

**Projeto 2:**

```bash
cd ecommerce-api-legacy && npm install && PORT=3055 npm start
```

```bash
curl -s -X POST localhost:3055/api/checkout -H 'Content-Type: application/json' -d '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
```

O relatório deve devolver a mesma ordem em chamadas repetidas:

```bash
for i in 1 2 3; do curl -s localhost:3055/api/admin/financial-report; echo; done
```

**Projeto 3:**

```bash
cd task-manager-api && pip install -r requirements.txt && python seed.py && PORT=5056 python app.py
```

```bash
curl -s localhost:5056/tasks/stats && curl -s localhost:5056/users/1
```

`GET /users/1` não deve conter o campo `password`. E o caso que antes dava 500:

```bash
curl -s -X POST localhost:5056/tasks -H 'Content-Type: application/json' -d '{"title":"Prioridade como string","priority":"3"}' -w '\n[%{http_code}]\n'
```

> **macOS:** as portas 5000 e 3000 costumam estar ocupadas (AirPlay Receiver e túneis SSH). Os
> comandos acima usam portas alternativas via a variável `PORT`, que os três projetos agora
> respeitam.

---

## Estrutura do repositório

```
.
├── README.md
├── reports/
│   ├── audit-project-1.md          # 22 findings
│   ├── audit-project-2.md          # 18 findings
│   └── audit-project-3.md          # 17 findings
├── code-smells-project/            # Python/Flask — E-commerce
│   ├── .claude/skills/refactor-arch/
│   ├── src/{config,models,controllers,views,middlewares,services}/
│   ├── app.py
│   └── scripts/reset_db.py
├── ecommerce-api-legacy/           # Node.js/Express — LMS
│   ├── .claude/skills/refactor-arch/
│   └── src/{config,models,controllers,routes,middlewares,services,errors,utils}/
└── task-manager-api/               # Python/Flask — Task Manager
    ├── .claude/skills/refactor-arch/
    ├── config/, models/, controllers/, routes/, middlewares/, services/, utils/
    └── app.py
```
