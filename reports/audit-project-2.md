================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js 26 + Express 4.18.2
Files:   3 analyzed | ~180 lines of code
Date:    2026-08-22

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js, CommonJS)
Framework:     Express 4.18.2
Dependencies:  sqlite3 5.1.6
Domain:        LMS API — usuários, cursos, matrículas, pagamentos e trilha de auditoria,
               com fluxo de checkout (cria usuário + cobra cartão + matricula)
Architecture:  God Class — AppManager.js concentra conexão, schema, seed, roteamento,
               regra de negócio de pagamento e montagem de resposta
Source files:  3 files analyzed (180 lines)
DB tables:     users, courses, enrollments, payments, audit_logs
Entry point:   src/app.js (npm start, porta 3000)
================================
```

O projeto tem apenas 180 linhas, mas densidade de problema alta: `AppManager.js` é uma God Class
literal, e `utils.js` — apesar do nome — é na verdade o arquivo de configuração com segredos de
produção, mais um cache global e uma função de hash caseira.

## Summary

CRITICAL: 6 | HIGH: 5 | MEDIUM: 3 | LOW: 4

O problema arquitetural de fundo é a God Class `AppManager`, que numa única classe abre o banco,
cria o schema, registra rotas, decide aprovação de pagamento e monta respostas — com o fluxo de
checkout inteiro dentro de uma pirâmide de 5 callbacks aninhados. O problema de segurança mais
urgente é o vazamento de dados de cartão e da chave `pk_live_` do gateway em log de texto puro,
confirmado nesta auditoria. O relatório financeiro apresentou **ordem não-determinística entre duas
chamadas idênticas**, evidenciando race condition real na orquestração assíncrona manual.

## Findings

### [CRITICAL] F01 — God Class (AP-C01)
- **File:** `src/AppManager.js:4-141`
- **Description:** Uma única classe com 5 responsabilidades incompatíveis: abre a conexão no
  construtor (`:7`), cria as 5 tabelas e insere os seeds (`:10-23`), registra as 3 rotas HTTP
  (`:25-138`), implementa a regra de aprovação de pagamento (`:46`) e monta os payloads de resposta
  (`:60`, `:121`). O método `setupRoutes(app)` (`:25-138`) sozinho tem 113 linhas.
- **Impact:** Não existe nenhuma unidade testável — verificar a regra "cartão que começa com 4 é
  aprovado" exige subir Express e SQLite. O truque `const self = this` (`:26`) existe justamente
  porque o escopo de `this` se perde nas callbacks aninhadas, sintoma de que fluxo e contexto estão
  misturados.
- **Recommendation:** Separar em `models/` (CourseModel, UserModel, EnrollmentModel),
  `services/PaymentGateway`, `controllers/CheckoutController` e `routes/`. Playbook §1.

### [CRITICAL] F02 — Hardcoded Production Credentials (AP-C02)
- **File:** `src/utils.js:1-7`
- **Description:** O objeto `config` traz, em literal, credenciais que se anunciam como de produção:
  `dbUser: "admin_master"`, `dbPass: "senha_super_secreta_prod_123"`,
  `paymentGatewayKey: "pk_live_1234567890abcdef"` e `smtpUser`. O prefixo `pk_live_` indica chave de
  gateway de pagamento em ambiente vivo. Nenhum valor vem de `process.env`.
- **Impact:** Chave de gateway de pagamento comprometida permite operações financeiras em nome da
  empresa. Está no histórico do git — remover do código não a remove do histórico.
- **Recommendation:** `config/index.js` lendo `process.env`, com `.env.example`. **Rotacionar a chave
  do gateway imediatamente**, antes de qualquer refatoração. Playbook §2.

### [CRITICAL] F03 — Card Data and Gateway Key Written to Logs (AP-C06)
- **File:** `src/AppManager.js:45`
- **Description:** O fluxo de checkout registra
  `` console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`) `` — o número
  completo do cartão recebido no corpo da requisição junto com a chave live do gateway, em texto
  puro.
- **Impact:** **Verificado nesta auditoria.** O log do servidor gravou
  `Processando cartão 4111222233334444 na chave pk_live_1234567890abcdef`. Números de cartão em log
  são violação direta de PCI-DSS (requisito 3.4); o log costuma ir para agregadores com controle de
  acesso mais frouxo que o do banco.
- **Recommendation:** Nunca logar PAN nem segredo. Se rastreabilidade for necessária, logar apenas os
  4 últimos dígitos. Playbook §6 e §12.

### [CRITICAL] F04 — Fake Cryptography for Passwords (AP-C05)
- **File:** `src/utils.js:17-23`, usado em `src/AppManager.js:68`
- **Description:** `badCrypto()` concatena 10.000 vezes os 2 primeiros caracteres do base64 da senha
  e devolve os 10 primeiros caracteres do resultado (`:22`). Não é hash: é uma transformação
  determinística, sem salt, cujo resultado é apenas a repetição de um par de caracteres derivado do
  início da senha.
- **Impact:** A saída tem entropia praticamente nula — o espaço de resultados é do tamanho do
  alfabeto base64 ao quadrado. Duas senhas com o mesmo primeiro caractere colidem, e o valor é
  reversível por inspeção. O laço de 10.000 iterações gasta CPU sem oferecer segurança alguma.
- **Recommendation:** `bcrypt`/`argon2`, ou `crypto.scrypt` da stdlib se adicionar dependência não
  for possível. Playbook §5.

### [CRITICAL] F05 — Payment Approved by Client-Controlled String (AP-C01)
- **File:** `src/AppManager.js:46-48`
- **Description:** A aprovação do pagamento é decidida por
  `let status = cc.startsWith("4") ? "PAID" : "DENIED"` — o valor do cartão vem do corpo da
  requisição e nenhuma chamada externa é feita. Em seguida grava-se `PAID` na tabela `payments`
  (`:54`) e a matrícula é efetivada.
- **Impact:** Qualquer pessoa se matricula em qualquer curso enviando `"card": "4"`. O sistema
  registra receita que não existe — o relatório financeiro (`:80-129`) soma esses valores como
  faturamento real.
- **Recommendation:** Integração real atrás de `services/PaymentGateway`, com o status vindo da
  resposta do gateway. Playbook §1 e §10.

### [CRITICAL] F06 — Missing Transaction Boundary and Orphan Rows (AP-C08)
- **File:** `src/AppManager.js:50-63`, `src/AppManager.js:131-137`
- **Description:** O checkout faz 3 escritas encadeadas — `enrollments` (`:50`), `payments` (`:54`),
  `audit_logs` (`:57`) — sem transação e sem rollback: uma falha na segunda deixa matrícula sem
  pagamento. Em `DELETE /api/users/:id` (`:131-137`) o usuário é removido sem tratar matrículas e
  pagamentos dependentes, e a própria resposta admite:
  `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` O callback ainda
  ignora o parâmetro `err` (`:133`) e sempre responde 200.
- **Impact:** **Verificado nesta auditoria.** Após `DELETE /api/users/1`, o relatório financeiro
  passou a exibir `{"student":"Unknown","paid":997}` — receita de 997 atribuída a um aluno que não
  existe mais. A base fica permanentemente inconsistente e o relatório contábil, incorreto.
- **Recommendation:** Envolver o checkout em transação (`BEGIN`/`COMMIT`/`ROLLBACK`); no delete,
  remover dependentes na mesma transação ou declarar `ON DELETE CASCADE`. Tratar `err` e devolver
  404 quando nada foi removido. Playbook §8.

### [HIGH] F07 — Callback Pyramid with Manual Async Orchestration (AP-H06)
- **File:** `src/AppManager.js:37-77`, `src/AppManager.js:80-129`
- **Description:** O checkout aninha 5 níveis de callback (`:37`, `:40`, `:50`, `:54`, `:57`). O
  relatório financeiro (`:80-129`) orquestra à mão duas contagens pendentes — `coursesPending`
  (`:86`) e `enrPending` (`:93`) — decrementadas dentro de `forEach` com chamadas assíncronas
  (`:89`, `:102`), e responde de **três** lugares diferentes (`:87`, `:98`, `:121`).
- **Impact:** **Verificado nesta auditoria.** Duas chamadas idênticas a
  `GET /api/admin/financial-report` devolveram os cursos em ordens diferentes — a primeira com
  Docker à frente, a segunda com Clean Architecture. A ordem do relatório depende de qual callback
  do SQLite retorna primeiro. Vários `err` são recebidos e ignorados (`:93`, `:104`, `:106`), então
  falhas de banco viram dados silenciosamente ausentes. Com `courses` vazio e um erro simultâneo, há
  caminho para dupla resposta e crash do processo.
- **Recommendation:** Promisificar o driver uma vez e reescrever o fluxo linearmente com
  `async/await`; substituir os contadores manuais por `Promise.all`. Playbook §11.

### [HIGH] F08 — Mutable Global State (AP-H03)
- **File:** `src/utils.js:9-15`, `src/utils.js:25`
- **Description:** `globalCache = {}` (`:9`) é um objeto de módulo alimentado por `logAndCache()`
  (`:12-15`) a cada checkout, com chave `last_checkout_${userId}` (`AppManager.js:59`). Não há
  limite de tamanho, TTL nem política de evicção. `totalRevenue` (`:10`) é exportado por valor
  (`:25`) e nunca atualizado.
- **Impact:** O cache cresce indefinidamente — uma entrada por usuário que já fez checkout — até
  esgotar a memória do processo. Como é estado de módulo, o valor não é compartilhado entre
  instâncias, então qualquer leitura futura seria inconsistente sob balanceamento de carga.
  `totalRevenue` exportado por valor é sempre `0` para quem importa: um bug latente.
- **Recommendation:** Cache com limite e evicção, injetado como dependência; remover `totalRevenue`.
  Playbook §9.

### [HIGH] F09 — Hardcoded Dependencies / No Injection (AP-H04)
- **File:** `src/AppManager.js:5-8`, `src/AppManager.js:1-2`
- **Description:** O construtor instancia sua própria conexão: `new sqlite3.Database(':memory:')`
  (`:7`). Config e helpers são importados concretamente no topo do módulo (`:2`). Nenhum
  colaborador é injetado.
- **Impact:** Impossível testar com um fake ou apontar para outro banco sem editar a classe. O banco
  `:memory:` fixo significa que **todos os dados somem a cada restart** — inclusive matrículas e
  pagamentos reais.
- **Recommendation:** Receber `db` e `config` por construtor; o composition root decide as
  implementações. Playbook §9.

### [HIGH] F10 — No Layer Separation: Routing + SQL in the Same Function (AP-H02)
- **File:** `src/AppManager.js:28-78`, `:80-129`, `:131-137`
- **Description:** Os três handlers executam SQL diretamente (`this.db.get`, `this.db.run`,
  `this.db.all`) dentro do próprio callback de rota. Não existe camada de model nem de controller.
- **Impact:** A regra de negócio do checkout só é alcançável por uma requisição HTTP; nenhuma query é
  reaproveitável; não há costura para transação ou autorização.
- **Recommendation:** Extrair models por tabela e um controller por caso de uso. Playbook §7.

### [HIGH] F11 — Unauthenticated Destructive Endpoint (AP-C07 rebaixado para HIGH)
- **File:** `src/AppManager.js:131-137`
- **Description:** `DELETE /api/users/:id` remove qualquer usuário por id, sem autenticação,
  autorização ou verificação de existência.
- **Impact:** Chamador anônimo apaga qualquer conta. Classificado HIGH e não CRITICAL porque o
  escopo é uma linha por chamada, não a base inteira — mas combinado com F06 cada exclusão corrompe
  permanentemente o relatório financeiro.
- **Recommendation:** Middleware de autenticação e checagem de papel; soft delete. Playbook §4.

### [MEDIUM] F12 — Scattered Error Handling with Ignored Errors (AP-M04, AP-M05)
- **File:** `src/AppManager.js:38`, `:41`, `:51`, `:55`, `:70`, `:84`, `:133`; erros ignorados em
  `:57`, `:93`, `:104`, `:106`
- **Description:** Cada callback repete seu próprio `if (err) return res.status(500).send("...")`,
  com mensagens diferentes a cada ponto (`"Erro DB"`, `"Erro Matrícula"`, `"Erro Pagamento"`). Em
  quatro pontos o `err` é recebido e simplesmente não testado. Não há middleware de erro
  `(err, req, res, next)` registrado em `app.js`.
- **Impact:** Falhas de banco no relatório viram campos ausentes em vez de erro — o cliente recebe
  200 com dados incompletos. As respostas de erro são `text/plain` enquanto as de sucesso são JSON.
- **Recommendation:** Classe `AppError`, `next(err)` nos controllers e um middleware de erro único
  registrado após as rotas. Playbook §12.

### [MEDIUM] F13 — Missing Input Validation (AP-M06)
- **File:** `src/AppManager.js:29-35`
- **Description:** A única validação é a presença de 4 campos (`:35`). Não há checagem de tipo,
  formato de e-mail, tamanho de senha nem formato de cartão. `p` (senha) não entra na validação e
  cai num default silencioso `"123456"` (`:68`). `cc.startsWith` (`:46`) assume string — um `card`
  numérico no JSON derruba o handler com `TypeError`.
- **Impact:** `{"card": 4111}` (número, não string) causa exceção não tratada dentro de um callback
  assíncrono, o que no Node derruba o processo inteiro. Usuários criados via checkout sem senha
  ficam todos com a mesma senha padrão.
- **Recommendation:** Camada de validação no controller, com tipos e formatos, antes de qualquer
  I/O. Playbook §14.

### [MEDIUM] F14 — Deprecated / Legacy API Usage (AP-M07)
- **File:** `src/AppManager.js:1`, e o estilo callback em `:37-77`, `:83-128`, `:133`
- **Description:** `require('sqlite3').verbose()` ativa o modo verboso do driver — destinado a
  depuração — de forma incondicional, inclusive em produção. Além disso, todo o acesso a banco usa a
  API callback-only do `sqlite3`, sem `util.promisify` nem wrapper de promise, mesmo o projeto
  rodando em Node 26 com `async/await` disponível.
- **Impact:** `.verbose()` acrescenta captura de stack trace a cada operação, com custo de
  performance e risco de expor caminhos internos em logs. O estilo callback é a causa direta da
  pirâmide e da race condition do F07.
- **Recommendation:** Remover `.verbose()` (ou condicioná-lo a `NODE_ENV !== 'production'`) e
  promisificar o driver uma vez em `models/Database.js`. Playbook §11 e §15.

### [LOW] F15 — Poor Naming (AP-L02)
- **File:** `src/AppManager.js:29-33`, `:43`, `:52`, `:86`, `:89`, `:90`, `:102`; `src/utils.js`
- **Description:** Variáveis de domínio com uma ou duas letras: `u`, `e`, `p`, `cid`, `cc` (`:29-33`),
  `c` (`:89`), `enr` (`:102`), `enrId` (`:52`). O arquivo `utils.js` não contém utilitários: contém
  configuração, cache global e criptografia. `AppManager` é um nome que não diz nada.
  (8 ocorrências agregadas.)
- **Impact:** `e` é e-mail em `:30` — mas `e` é a convenção universal para `error` em JavaScript,
  o que induz a erro na leitura. O nome `utils.js` esconde que ali estão os segredos de produção.
- **Recommendation:** Renomear para o vocabulário do domínio e mover cada bloco para o módulo certo.
  O formato de wire (`usr`, `eml`, `c_id`) deve ser preservado — renomear só os identificadores
  internos, via desestruturação com alias. Playbook §16.

### [LOW] F16 — Magic Values in Business Rules (AP-L01)
- **File:** `src/AppManager.js:46`, `:48`, `:108`; `src/utils.js:6`, `:19`, `:22`
- **Description:** `"4"` como prefixo de cartão aprovado (`:46`), os literais de status `"PAID"` /
  `"DENIED"` (`:46`, `:108`), a porta `3000` (`utils.js:6`) e as constantes `10000` e `2` do
  `badCrypto` (`utils.js:19-22`). (6 ocorrências agregadas.)
- **Impact:** A regra de aprovação de pagamento — a decisão mais crítica do sistema — é um literal
  invisível no meio de um ternário.
- **Recommendation:** Enum de status e constantes nomeadas em `config/`. Playbook §14.

### [LOW] F17 — console.log as Logging (AP-L03)
- **File:** `src/AppManager.js:45`; `src/utils.js:13`; `src/app.js:13`
- **Description:** Logging via `console.log` com template literal, sem nível, timestamp ou
  estruturação. (3 ocorrências agregadas — a de `:45` é reportada separadamente como F03 por conter
  dado de cartão.)
- **Impact:** Não há como filtrar por severidade nem desligar em produção.
- **Recommendation:** Logger com níveis, injetado. Playbook §12.

### [LOW] F18 — Inconsistent Response Contract (AP-L05)
- **File:** `src/AppManager.js:35`, `:38`, `:48`, `:60`, `:98`, `:135`
- **Description:** Sucessos ora devolvem JSON (`{msg, enrollment_id}` em `:60`, array em `:98`), ora
  texto puro (`:135`). Erros são sempre texto puro (`"Bad Request"`, `"Curso não encontrado"`,
  `"Pagamento recusado"`), sem corpo estruturado.
- **Impact:** O cliente precisa inspecionar o `Content-Type` para saber como interpretar cada
  resposta; erros não têm código de máquina.
- **Recommendation:** Envelope JSON consistente. **Preservar o shape atual de cada endpoint** nesta
  refatoração. Playbook §12.

## Deprecated APIs

Varredura executada para Node.js (`new Buffer`, `url.parse`, `crypto.createCipher`, `util.isArray`,
`util._extend`, `process.binding`, `fs.exists`, `app.del`, `res.send(status)`):

| API | Location | Deprecated since | Replacement |
|---|---|---|---|
| `require('sqlite3').verbose()` em produção | `src/AppManager.js:1` | — (modo de depuração) | remover, ou condicionar a `NODE_ENV !== 'production'` |
| API callback-only do `sqlite3` | `src/AppManager.js:37-77`, `:83-128`, `:133` | — (estilo legado) | `util.promisify` ou wrapper de promise + `async/await` |

`Buffer.from()` em `src/utils.js:20` já é a forma correta — o `new Buffer()` deprecado (DEP0005)
**não** está presente. Nenhuma outra API deprecada da lista foi encontrada.

## Proposed Target Structure

```
src/
├── config/
│   └── index.js               # process.env, sem segredos literais
├── models/
│   ├── Database.js            # driver promisificado + transaction()
│   ├── schema.js              # createTables() + seed() explícitos
│   ├── UserModel.js
│   ├── CourseModel.js
│   ├── EnrollmentModel.js
│   ├── PaymentModel.js
│   └── AuditLogModel.js
├── controllers/
│   ├── CheckoutController.js
│   ├── ReportController.js
│   └── UserController.js
├── routes/
│   ├── index.js
│   ├── checkoutRoutes.js
│   ├── reportRoutes.js
│   └── userRoutes.js
├── middlewares/
│   ├── errorHandler.js
│   └── validateBody.js
├── services/
│   └── PaymentGateway.js      # integração externa atrás de interface
├── errors/AppError.js
├── utils/logger.js            # utilitário de verdade
└── app.js                     # buildApp() — composition root
```

## Migration Risk

Mudanças de comportamento propostas, cada uma justificada por um finding:

1. **Número de cartão e chave do gateway deixam de ser logados** (F03). Nenhuma mudança no contrato
   HTTP — apenas no log do servidor.
2. **`DELETE /api/users/:id` passa a remover matrículas e pagamentos dependentes na mesma
   transação** (F06). A mensagem de resposta muda de
   `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` para uma confirmação
   correta, e um id inexistente passa a devolver 404 em vez de 200 — hoje o `err` é ignorado.
3. **`GET /api/admin/financial-report` passa a ter ordem determinística** (F07). O conteúdo é o
   mesmo; a ordem, que hoje varia entre chamadas, passa a ser estável (por id de curso).
4. **Senhas passam a usar hash real** (F04). Usuários criados pelo checkout antigo não conseguirão
   autenticar com o hash antigo — como não existe endpoint de login neste projeto, o impacto
   observável é nulo, mas o banco é `:memory:` e reinicia limpo a cada boot de qualquer forma.
5. **A aprovação de pagamento continua simulada** (F05), agora isolada atrás de
   `services/PaymentGateway` com a mesma regra (`card` iniciando em `4` → `PAID`), para preservar o
   comportamento dos exemplos em `api.http`. A troca por um gateway real fica como ponto de extensão
   documentado — mudar a regra agora quebraria os testes manuais existentes.
6. **`POST /api/checkout` com `card` não-string passa a devolver 400** em vez de derrubar o processo
   (F13).

Os 3 endpoints mantêm path, método e status codes de sucesso idênticos.

================================
Total: 18 findings
================================
