# Reference — Project Analysis Heuristics (Phase 1)

Goal: describe the project accurately enough that the audit and the refactor can be
technology-appropriate. Detection is evidence-based — every field you print must come from a
file you read.

## 0. Inventory

List all files, excluding: `node_modules/`, `.venv/`, `venv/`, `env/`, `__pycache__/`,
`.git/`, `dist/`, `build/`, `target/`, `vendor/`, `*.lock`, `package-lock.json`, `*.db`,
`*.sqlite`, `coverage/`, `.next/`.

Count source files and total lines. Read **all** of them if the project is under ~3000 lines;
above that, read every file that the entry point reaches transitively.

## 1. Language detection

| Signal | Language |
|---|---|
| `*.py`, `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` | Python |
| `*.js`, `*.mjs`, `*.cjs`, `package.json` | JavaScript / Node.js |
| `*.ts`, `tsconfig.json` | TypeScript |
| `*.go`, `go.mod` | Go |
| `*.rb`, `Gemfile` | Ruby |
| `*.php`, `composer.json` | PHP |
| `*.java`, `pom.xml`, `build.gradle` | Java |
| `*.cs`, `*.csproj` | C# |

If several are present, the language of the entry point (the file the run script invokes) wins;
mention the others as secondary.

Runtime version: `python_requires`, `engines` in `package.json`, `go 1.x` in `go.mod`,
`.python-version`, `.nvmrc`, `Dockerfile` base image.

## 2. Framework detection

Read the manifest first — it gives you the pinned version. Confirm with an import in the code.

**Python**
- `flask` in requirements + `Flask(__name__)` → Flask
- `django` + `manage.py`, `settings.py` → Django
- `fastapi` + `FastAPI()` → FastAPI
- `flask-sqlalchemy` / `sqlalchemy` → SQLAlchemy ORM
- `marshmallow`, `pydantic` → schema/validation layer available

**Node.js**
- `express` + `express()` → Express (check `4.x` vs `5.x`: error-handling and router
  semantics differ)
- `fastify`, `koa`, `@nestjs/core`, `next` → Fastify / Koa / NestJS / Next.js
- `sequelize`, `prisma`, `typeorm`, `mongoose`, `knex` → ORM/query layer
- No framework import but `http.createServer` → raw Node

**Others**: `gin-gonic`/`echo`/`fiber` (Go), `rails`/`sinatra` (Ruby), `laravel`/`symfony`
(PHP), `spring-boot` (Java).

Print the framework **with the version from the manifest**, not a guess.

## 3. Database detection

Look, in order, for:
1. **Driver in the manifest**: `sqlite3`, `psycopg2`, `pymysql`, `mysql2`, `pg`, `mongoose`,
   `redis`, `flask-sqlalchemy`.
2. **Connection setup in code**: `sqlite3.connect(...)`, `new sqlite3.Database(...)`,
   `SQLALCHEMY_DATABASE_URI`, `DATABASE_URL`, `createPool`, `MongoClient`.
3. **Schema**: every `CREATE TABLE <name>` and every ORM model class
   (`class X(db.Model)`, `sequelize.define`, `@Entity`). List the table names — they are the
   fastest route to the domain.
4. **Access style**: raw SQL strings / query builder / ORM / mixed. Note it — the refactor
   strategy for a model layer depends on it.

Also flag: in-memory databases (`:memory:`), auto-created schema at import time, seed data
embedded in the connection helper.

## 4. Domain inference

Combine three sources and write **one line** of plain language:
- Route paths (`/produtos`, `/api/checkout`, `/tasks`)
- Table / model names (`pedidos`, `enrollments`, `categories`)
- Entity fields (`preco`, `estoque` → commerce; `due_date`, `priority` → task tracking;
  `course_id`, `enrollment` → education/LMS)

Keep the domain vocabulary in the language the code uses. Do not translate `produtos` to
`products` in the report — the refactor should not rename the domain.

## 5. Current architecture mapping

For every source file, answer four questions and record the answer:

| Question | How to tell |
|---|---|
| Does it define routes? | `@app.route`, `app.get/post/...`, `add_url_rule`, `Blueprint`, `Router()` |
| Does it touch the database? | `cursor.execute`, `db.run/get/all`, `.query.`, `session.add` |
| Does it hold business rules? | branching on domain state, price/total computation, status transitions, validation |
| Does it do I/O side effects? | `print`, `console.log`, `smtplib`, `fetch`, file writes |

Then classify:

- **Monolithic / God file** — one file answers yes to 3 or more questions.
- **Flat split, no layering** — files split by *technical noun* (`models.py`, `controllers.py`)
  but persistence, validation and business logic still mixed inside each.
- **Partially layered** — real directories (`models/`, `routes/`, `services/`) exist, but the
  dependency rule is violated (routes query the DB directly, models perform I/O, no controller
  layer between route and model).
- **Layered MVC** — routes delegate to controllers, controllers orchestrate models, models own
  persistence only.

State the classification **and the evidence** for it, e.g.
`Partially layered — routes/ exists but routes/task_routes.py:14-59 builds DTOs and runs queries directly`.

## 6. Entry point and run command

Find how the app boots: `if __name__ == "__main__"`, `scripts.start` in `package.json`,
`main` field, `Procfile`, `Dockerfile CMD`, README instructions. Record the port. You will
need this exact command to validate in Phase 3.

Also record any **prerequisite step** the README mentions (a `seed.py`, a migration, an env
file) — skipping it makes the Phase 3 validation produce false failures.
