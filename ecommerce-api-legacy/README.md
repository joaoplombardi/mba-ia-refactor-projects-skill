# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express, refatorada para MVC pela skill `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e carrega seeds
automaticamente no boot. Exemplos de requisições estão em `api.http`.

## Configuração

Todos os valores vêm do ambiente — veja `.env.example`. Nenhum segredo está no código.

| Variável | Default | Descrição |
|---|---|---|
| `PORT` | `3000` | Porta do servidor. |
| `DB_FILE` | `:memory:` | Arquivo SQLite. |
| `SEED_ON_BOOT` | `1` | Popula o banco vazio no boot. |
| `LOG_LEVEL` | `info` | `error`, `warn`, `info` ou `debug`. |
| `PAYMENT_GATEWAY_KEY` | — | Obrigatória em produção. |
| `PAYMENT_MODE` | `simulated` fora de produção | `simulated` não cobra nada. Produção exige `live` explícito. |
| `APPROVED_CARD_PREFIX` | `4` | Prefixo de cartão aprovado pelo gateway simulado. |
| `ADMIN_API_TOKEN` | — | Habilita `DELETE /api/users/:id`. Sem ele o endpoint responde 503. |

> A chave `pk_live_...` que estava fixa em `src/utils.js` precisa ser **rotacionada**: removê-la
> do código não a remove do histórico do git.

## Estrutura

```
src/
├── config/          index.js — process.env, sem segredos literais
├── models/          Database.js (driver promisificado + transaction), schema.js e um model por tabela
├── controllers/     CheckoutController, ReportController, UserController
├── routes/          express.Router por recurso — apenas wiring
├── middlewares/     errorHandler.js — registro único, após as rotas
├── services/        PaymentGateway.js — integração externa atrás de interface
├── errors/          AppError.js e subclasses de domínio
├── utils/           logger.js (com máscara de cartão), passwords.js (scrypt)
└── app.js           buildApp() — composition root
```

## Mudanças de comportamento

Os 3 endpoints mantêm path, método e status codes idênticos. As diferenças:

- **`GET /api/admin/financial-report` agora é determinístico.** Antes, duas chamadas idênticas
  devolviam os cursos em ordens diferentes — a orquestração assíncrona manual respondia na ordem
  em que os callbacks retornavam. Agora a ordem segue o id do curso.
- **`DELETE /api/users/:id` remove matrículas e pagamentos junto**, na mesma transação. Antes
  deixava linhas órfãs e o relatório financeiro passava a atribuir receita a `"student":"Unknown"`.
  Um id inexistente agora devolve 404 — antes o erro do driver era ignorado e a resposta era 200.
- **Número de cartão e chave do gateway não são mais logados.** O log registra apenas os 4 últimos
  dígitos.
- **`card` não-string devolve 400** em vez de derrubar o processo.
- **`DELETE /api/users/:id` exige `Authorization: Bearer <ADMIN_API_TOKEN>`** (finding F11). Sem
  credencial devolve 401; sem `ADMIN_API_TOKEN` configurado, 503 — o endpoint fica desabilitado,
  nunca aberto. Antes qualquer chamador anônimo apagava qualquer conta.

## Pagamento: o gateway é simulado

`SimulatedPaymentGateway` **não cobra nada** — aprova pelo prefixo do cartão, que era a regra do
código legado (finding F05). A refatoração não cria uma integração real; o que ela garante é que o
simulador não possa ser confundido com um gateway de verdade:

- avisa em `warn` no boot e a cada cobrança;
- marca o resultado com `simulated: true`;
- em produção a aplicação **recusa bootar** sem `PAYMENT_MODE=live`;
- com `PAYMENT_MODE=live` também recusa bootar, porque não há provedor real integrado.

**Risco residual:** em desenvolvimento e staging, qualquer cartão começando com `4` matricula sem
pagar. Fechar isso exige integrar um provedor real atrás da interface `charge()`.
