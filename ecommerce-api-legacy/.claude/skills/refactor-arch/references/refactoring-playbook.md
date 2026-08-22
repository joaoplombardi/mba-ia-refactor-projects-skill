# Reference — Refactoring Playbook (Phase 3)

One section per anti-pattern family. Each gives the transformation, a before/after pair, and
the check that proves it worked. Examples alternate Python and JavaScript — the *shape* of the
transformation is the same in any language.

Golden rule: **move code, don't rewrite it**. Port existing rules verbatim into their new
layer, then clean them up. A refactor that changes behaviour by accident is a regression.

---

## §1 — Split a God Class into layers  (AP-C01, AP-H01)

Work outside-in: peel routing off first, then persistence, and whatever is left in the middle
is the business logic that belongs in a controller.

1. List every route the god file registers → they become `routes/`.
2. List every query it runs → they become `models/`, grouped by table.
3. What remains — validation, arithmetic, orchestration — becomes `controllers/`.
4. Replace the god file with the composition root.

**Before** — `AppManager.js`: constructor opens the DB, `setupRoutes` holds routing, SQL,
payment rules and response building.

```js
class AppManager {
    constructor() { this.db = new sqlite3.Database(':memory:'); }
    setupRoutes(app) {
        app.post('/api/checkout', (req, res) => {
            this.db.get("SELECT * FROM courses WHERE id = ?", [req.body.c_id], (err, course) => {
                let status = req.body.card.startsWith("4") ? "PAID" : "DENIED";
                this.db.run("INSERT INTO enrollments ...", [...], function (err) { /* ... */ });
            });
        });
    }
}
```

**After** — four files, each with one reason to change:

```js
// models/CourseModel.js  — persistence only
class CourseModel {
    constructor(db) { this.db = db; }
    findActiveById(id) {
        return this.db.get("SELECT * FROM courses WHERE id = ? AND active = 1", [id]);
    }
}

// services/PaymentGateway.js — the external system, behind an interface
class PaymentGateway {
    constructor({ apiKey }) { this.apiKey = apiKey; }
    async charge({ card, amount }) { /* ... */ return { status: 'PAID' }; }
}

// controllers/CheckoutController.js — the use case
class CheckoutController {
    constructor({ courseModel, userModel, enrollmentModel, paymentGateway, db }) { /* ... */ }
    async checkout(input) {
        const course = await this.courseModel.findActiveById(input.courseId);
        if (!course) throw new NotFoundError('Curso não encontrado');
        const payment = await this.paymentGateway.charge({ card: input.card, amount: course.price });
        if (payment.status !== 'PAID') throw new PaymentDeniedError('Pagamento recusado');
        return this.db.transaction(async () => { /* enrol + record payment + audit */ });
    }
}

// routes/checkoutRoutes.js — wiring only
router.post('/api/checkout', (req, res, next) =>
    controller.checkout(mapRequest(req)).then(r => res.status(200).json(r)).catch(next));
```

**Check:** the god file no longer exists; no file matches both `app\.(get|post)` and `execute|db\.(run|get|all)`.

---

## §2 — Externalize configuration and secrets  (AP-C02, AP-H07)

Every secret becomes an environment variable. Provide a dev default only for values that are
not secret; a real credential gets **no** default.

**Before**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
```
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_1234567890abcdef" };
```

**After**
```python
# config/settings.py
import os

class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    DEBUG      = os.environ.get("FLASK_DEBUG", "0") == "1"
    DB_PATH    = os.environ.get("DB_PATH", "loja.db")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

    @classmethod
    def validate(cls):
        if not cls.DEBUG and cls.SECRET_KEY == "dev-only-insecure-key":
            raise RuntimeError("SECRET_KEY must be set in production")

settings = Settings()
```

Also ship `.env.example`:
```
SECRET_KEY=
DB_PATH=loja.db
FLASK_DEBUG=0
CORS_ORIGINS=http://localhost:3000
```

Add `.env` to `.gitignore`. Note in the report that any secret already committed must be
**rotated** — removing it from the code does not remove it from git history.

**Check:** grep for the old literals returns nothing; the app boots with no env vars set.

---

## §3 — Parameterize every query  (AP-C03)

Never build SQL with `+`, f-strings, `%` or template literals. Values go through placeholders;
only *identifiers you control* may be interpolated, and only from an allowlist.

**Before**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))
```

**After**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))
```

Dynamic filters — build the *structure* from code, the *values* from parameters:

**Before**
```python
query = "SELECT * FROM produtos WHERE 1=1"
if termo:      query += " AND (nome LIKE '%" + termo + "%')"
if categoria:  query += " AND categoria = '" + categoria + "'"
if preco_min:  query += " AND preco >= " + str(preco_min)
cursor.execute(query)
```

**After**
```python
clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    clauses.append("categoria = ?")
    params.append(categoria)
if preco_min is not None:
    clauses.append("preco >= ?")
    params.append(preco_min)

cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params)
```

The f-string here interpolates only clause fragments the code itself produced — no user input
reaches the SQL text.

For sort columns: `if sort not in ALLOWED_SORTS: raise ValidationError(...)` then interpolate.

**Check:** no line matches a SQL keyword adjacent to `+`, `%`, `${` or an f-string brace.
`POST /login` with `{"email": "' OR '1'='1"}` returns 401, not 200.

---

## §4 — Remove arbitrary-execution and unguarded destructive endpoints  (AP-C04, AP-C07)

There is no safe way to expose "run this SQL". Delete the route. For destructive admin
operations, either delete them or put them behind an auth guard **and** an explicit
confirmation parameter.

**Before**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json().get("sql", ""))   # arbitrary SQL from the internet

@app.route("/admin/reset-db", methods=["POST"])
def reset_database():
    cursor.execute("DELETE FROM pedidos")               # no auth at all
```

**After** — `/admin/query` is gone. The reset survives only as a CLI task:
```python
# scripts/reset_db.py — runnable by an operator with shell access, not by an HTTP caller
if __name__ == "__main__":
    if os.environ.get("ALLOW_DB_RESET") != "yes":
        raise SystemExit("Set ALLOW_DB_RESET=yes to run this destructive script.")
    reset_all_tables()
```

If a route must stay, guard it:
```python
@admin_bp.route("/admin/reset-db", methods=["POST"])
@require_role("admin")
def reset_database():
    ...
```

Removing a route is a behaviour change — list it under "Behaviour changes" with the finding ID.

**Check:** `POST /admin/query` returns 404. No handler passes request data to `execute`,
`eval`, `exec` or a shell.

---

## §5 — Fix password storage  (AP-C05)

Use a purpose-built password hash (bcrypt, argon2, scrypt, PBKDF2). Never MD5, SHA-1, a bare
SHA-256, or a hand-rolled function.

**Before**
```python
def set_password(self, pwd):   self.password = hashlib.md5(pwd.encode()).hexdigest()
def check_password(self, pwd): return self.password == hashlib.md5(pwd.encode()).hexdigest()
```
```js
function badCrypto(pwd) {                    // "hash" that is neither salted nor one-way
    let hash = "";
    for (let i = 0; i < 10000; i++) hash += Buffer.from(pwd).toString('base64').substring(0, 2);
    return hash.substring(0, 10);
}
```

**After** — prefer the standard library when adding a dependency is not an option:
```python
from werkzeug.security import generate_password_hash, check_password_hash   # ships with Flask

def set_password(self, raw_password):
    self.password = generate_password_hash(raw_password)     # salted PBKDF2-SHA256

def check_password(self, raw_password):
    return check_password_hash(self.password, raw_password)
```

Migration: existing hashes cannot be converted. Either re-seed the dev database, or accept the
old format once and upgrade transparently on the next successful login. State which you chose
under "Behaviour changes" — if existing users must reset their password, say so.

**Check:** no `md5`/`sha1` in an auth path; two users with the same password have different
stored hashes; login still succeeds after re-seeding.

---

## §6 — Stop leaking sensitive fields  (AP-C06, AP-M03)

Serialization is explicit and lives in one place per entity. Credentials never appear in a
response; `SELECT *` never feeds one directly.

**Before**
```python
def to_dict(self):
    return {'id': self.id, 'name': self.name, 'email': self.email,
            'password': self.password,          # leaked to every caller
            'role': self.role}
```
```python
return jsonify({"status": "ok", "debug": True,
                "secret_key": "minha-chave-super-secreta-123"})   # health endpoint
```

**After**
```python
PUBLIC_FIELDS = ('id', 'name', 'email', 'role', 'active', 'created_at')

def to_dict(self):
    """Public representation. Never includes credentials."""
    return {f: _serialize(getattr(self, f)) for f in PUBLIC_FIELDS}
```
```python
return jsonify({"status": "ok", "database": "connected", "counts": counts, "versao": VERSION})
```

Dropping a field is a behaviour change — list it, justified by the finding.

**Check:** grep the response builders for `password|senha|secret|token` → no hits.
`GET /users` and `GET /health` contain no credential material.

---

## §7 — Extract a controller between route and model  (AP-H01, AP-H02)

The route becomes wiring. Validation and orchestration move to the controller. Queries move to
the model.

**Before** — a Flask route that validates, queries, computes and serializes:
```python
@task_bp.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data:                    return jsonify({'error': 'Dados inválidos'}), 400
    if len(data['title']) < 3:      return jsonify({'error': 'Título muito curto'}), 400
    if data['priority'] < 1 or data['priority'] > 5:
                                    return jsonify({'error': 'Prioridade...'}), 400
    user = User.query.get(data['user_id'])
    if not user:                    return jsonify({'error': 'Usuário não encontrado'}), 404
    task = Task(); task.title = data['title']; ...
    db.session.add(task); db.session.commit()
    return jsonify(task.to_dict()), 201
```

**After**
```python
# views/task_routes.py — wiring only
@task_bp.route('/tasks', methods=['POST'])
def create_task():
    task = task_controller.create(request.get_json())
    return jsonify(task.to_dict()), 201

# controllers/task_controller.py — the use case
def create(payload):
    data = TaskValidator.validate_create(payload)        # raises ValidationError → 400
    if data.get('user_id') and not user_repository.exists(data['user_id']):
        raise NotFoundError('Usuário não encontrado')    # → 404
    return task_repository.create(data)

# models/task_repository.py — persistence only
def create(data):
    task = Task(**data)
    db.session.add(task)
    db.session.commit()
    return task
```

Status codes are preserved: `ValidationError → 400`, `NotFoundError → 404`, mapped once in the
error middleware (§12).

**Check:** no `.query.`, `session.` or `cursor.execute` under `views/` or `routes/`; no route
handler longer than ~5 lines.

---

## §8 — Introduce transaction boundaries  (AP-C08)

A use case that writes more than once either commits entirely or not at all. The boundary lives
in the controller, never in the model.

**Before** — stock is decremented row by row, no rollback if the third item fails:
```python
for item in itens:
    cursor.execute("INSERT INTO itens_pedido ...")
    cursor.execute("UPDATE produtos SET estoque = estoque - ...")
db.commit()
```

**After**
```python
# models/db.py
@contextmanager
def transaction(conn):
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise

# controllers/pedido_controller.py
with transaction(db) as cursor:
    pedido_id = pedido_model.create(cursor, usuario_id, total)
    for item in itens:
        pedido_model.add_item(cursor, pedido_id, item)
        produto_model.decrement_stock(cursor, item['produto_id'], item['quantidade'])
```

Guard the invariant inside the same transaction so two concurrent orders cannot both pass the
stock check:
```sql
UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?
-- rowcount 0 → insufficient stock → raise → rollback
```

For a parent delete with dependants, delete the children in the same transaction (or declare
`ON DELETE CASCADE`) instead of leaving orphans.

**Check:** kill the process mid-operation, or force an error on the last write — no partial
rows remain.

---

## §9 — Replace global state with injected dependencies  (AP-H03, AP-H04)

Collaborators arrive through the constructor or a factory argument. The composition root is the
only place that decides which concrete implementation is used.

**Before**
```python
db_connection = None                      # module-level mutable global

def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
    return db_connection

def get_produto_por_id(id):
    db = get_db()                          # hidden dependency, unfakeable in a test
```
```js
let globalCache = {};                      // grows forever, shared by every request
function logAndCache(key, data) { globalCache[key] = data; }
```

**After**
```python
# models/database.py
class Database:
    def __init__(self, db_path):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
    def cursor(self): return self._conn.cursor()

# models/produto_model.py
class ProdutoModel:
    def __init__(self, db):                # dependency injected
        self.db = db
    def get_by_id(self, produto_id):
        cur = self.db.cursor()
        cur.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
        return _row_to_dict(cur.fetchone())

# app.py — composition root
db = Database(settings.DB_PATH)
produto_model = ProdutoModel(db)
produto_controller = ProdutoController(produto_model)
```

Schema creation and seeding move out of the connection helper into an explicit
`init_schema(db)` / `seed(db)` called by the composition root — connecting to a database should
never have the side effect of creating tables.

For a cache, use a bounded structure with an eviction policy, injected like any other
collaborator — not a module-level dict.

**Check:** no `global` statements; no module-level mutable containers; a test can construct a
model with an in-memory database and no monkey-patching.

---

## §10 — Move side effects out of models  (AP-H05)

The model saves. The controller decides that a notification should happen. A service performs it.

**Before**
```python
class NotificationService:
    def __init__(self):
        self.email_password = 'senha123'        # secret, and a live SMTP client in the model layer
    def notify_task_assigned(self, user, task):
        server = smtplib.SMTP(self.email_host, self.email_port)   # blocking I/O on the request path
```
```python
# controller
print("ENVIANDO EMAIL: Pedido " + str(pedido_id))   # a side effect faked with print
```

**After**
```python
# services/email_client.py — the external system behind an interface
class EmailClient:
    def __init__(self, host, port, user, password, enabled=True):
        ...
    def send(self, to, subject, body): ...

class NullEmailClient:          # injected in dev/test — no network, no credentials needed
    def send(self, to, subject, body):
        logger.info("email suppressed", extra={"to": to, "subject": subject})

# controllers/pedido_controller.py
pedido = self.pedido_model.create(...)          # persistence
self.notifier.order_created(pedido)             # decision to notify lives here
```

Credentials come from config (§2). The composition root injects `EmailClient` or
`NullEmailClient` based on configuration, so the app boots without SMTP access.

**Check:** no `smtplib`/`fetch`/`requests` import under `models/`; no business `print` there.

---

## §11 — Flatten the callback pyramid  (AP-H06)

Promisify the driver once, then write the use case linearly. One response per request, one
error path.

**Before**
```js
this.db.get("SELECT ...", [cid], (err, course) => {
    this.db.get("SELECT ...", [e], (err, user) => {
        this.db.run("INSERT ...", [...], function (err) {
            self.db.run("INSERT ...", [...], function (err) {
                self.db.run("INSERT ...", [...], (err) => { res.status(200).json({...}); });
            });
        });
    });
});
```

**After**
```js
// models/Database.js — promisify the callback driver once
const { promisify } = require('util');

class Database {
    constructor(sqliteDb) {
        this.db  = sqliteDb;
        this.get = promisify(sqliteDb.get.bind(sqliteDb));
        this.all = promisify(sqliteDb.all.bind(sqliteDb));
    }
    run(sql, params = []) {                       // `this.lastID` needs a manual wrapper
        return new Promise((resolve, reject) => {
            this.db.run(sql, params, function (err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            });
        });
    }
}

// controllers/CheckoutController.js — linear, every error propagates to one handler
async checkout(input) {
    const course = await this.courseModel.findActiveById(input.courseId);
    if (!course) throw new NotFoundError('Curso não encontrado');
    const user   = await this.userModel.findOrCreateByEmail(input);
    const result = await this.enrollmentModel.enrol(user.id, course);
    return { msg: 'Sucesso', enrollment_id: result.enrollmentId };
}
```

The same applies to the hand-rolled pending counter — replace it with `Promise.all`:

**Before**
```js
let pending = courses.length;
courses.forEach(c => { /* ... */ pending--; if (pending === 0) res.json(report); });
```
**After**
```js
const report = await Promise.all(courses.map(c => this.buildCourseReport(c)));
```

**Check:** no callback nesting deeper than one level; no `pending--` counters; every `err` is
either handled or propagated; a forced failure produces exactly one response.

---

## §12 — Centralize error handling and logging  (AP-M04, AP-M05, AP-H07, AP-L03)

Define domain errors, throw them from controllers, and map them to HTTP in exactly one place.
Log the real cause server-side; return a safe message to the client.

**Before** — repeated in every one of 20 handlers:
```python
except Exception as e:
    print("ERRO: " + str(e))
    return jsonify({"erro": str(e)}), 500      # internal detail sent to the client
```

**After**
```python
# errors.py
class AppError(Exception):
    status_code = 500
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code: self.status_code = status_code

class ValidationError(AppError): status_code = 400
class NotFoundError(AppError):   status_code = 404
class ConflictError(AppError):   status_code = 409

# middlewares/error_handler.py
def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        logger.warning("%s: %s", type(err).__name__, err.message)
        return jsonify({"erro": err.message, "sucesso": False}), err.status_code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Unhandled error")            # full trace in the server log
        return jsonify({"erro": "Erro interno do servidor", "sucesso": False}), 500
```

Express equivalent — the error middleware is registered **after** all routes, with four
parameters, and async handlers forward via `next`:
```js
app.use((err, req, res, next) => {
    logger.error(err);
    const status = err.statusCode || 500;
    res.status(status).json({ error: status === 500 ? 'Erro interno' : err.message });
});
```

Replace `print`/`console.log` with a levelled logger. Never log card numbers, passwords or
secrets — that is AP-C06, not a logging nit.

**Check:** no `except Exception ... 500` inside handlers; no `str(e)` in a response body;
an induced failure returns the standard envelope and writes one log line.

---

## §13 — Eliminate N+1 queries  (AP-M01)

Fetch the set in one query — a JOIN, an `IN (...)`, or the ORM's eager-loading option — then
group in memory.

**Before** — 1 + N + N×M queries to build an order list:
```python
for row in pedidos:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in itens:
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```

**After** — 2 queries regardless of size:
```python
cur.execute("SELECT * FROM pedidos WHERE usuario_id = ?", (usuario_id,))
pedidos = [dict(r) for r in cur.fetchall()]
if not pedidos:
    return []

ids = [p["id"] for p in pedidos]
placeholders = ",".join("?" * len(ids))                 # structure from code, values as params
cur.execute(f"""
    SELECT ip.pedido_id, ip.produto_id, ip.quantidade, ip.preco_unitario,
           COALESCE(p.nome, 'Desconhecido') AS produto_nome
      FROM itens_pedido ip
      LEFT JOIN produtos p ON p.id = ip.produto_id
     WHERE ip.pedido_id IN ({placeholders})
""", ids)

itens_por_pedido = defaultdict(list)
for item in cur.fetchall():
    itens_por_pedido[item["pedido_id"]].append(dict(item))
for pedido in pedidos:
    pedido["itens"] = itens_por_pedido[pedido["id"]]
```

ORM form — replace the in-loop lookup with eager loading:
```python
tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
```

Counter aggregations follow the same rule — one `GROUP BY` instead of one `COUNT` per bucket:
```python
cur.execute("SELECT status, COUNT(*) AS n FROM pedidos GROUP BY status")
```

**Check:** no query call inside a loop; the query count for a list endpoint is constant as rows
grow.

---

## §14 — Unify validation and serialization  (AP-M02, AP-M03, AP-M06, AP-L01)

One validator per entity, used by every operation. One serializer per entity, used by every
response. Bounds become named constants.

**Before** — the same rules, written twice, drifting:
```python
# create_task
if len(title) < 3:                              return jsonify({'error': 'Título muito curto'}), 400
if priority < 1 or priority > 5:                return jsonify({'error': 'Prioridade...'}), 400
# update_task — same rules, re-typed; `status` list repeated in 4 files
if len(data['title']) < 3:                      return jsonify({'error': 'Título muito curto'}), 400
```

**After**
```python
# config/constants.py
MIN_TITLE_LENGTH, MAX_TITLE_LENGTH = 3, 200
MIN_PRIORITY, MAX_PRIORITY = 1, 5
VALID_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')

# controllers/validators/task_validator.py
class TaskValidator:
    @staticmethod
    def validate_create(payload):
        data = _require_object(payload)
        return {
            'title':    TaskValidator._title(data, required=True),
            'status':   TaskValidator._status(data),
            'priority': TaskValidator._priority(data),
        }

    @staticmethod
    def validate_update(payload):
        """Same rules, applied only to the keys present."""
        data = _require_object(payload)
        out = {}
        if 'title' in data:    out['title']    = TaskValidator._title(data, required=True)
        if 'status' in data:   out['status']   = TaskValidator._status(data)
        if 'priority' in data: out['priority'] = TaskValidator._priority(data)
        return out

    @staticmethod
    def _priority(data):
        raw = data.get('priority', DEFAULT_PRIORITY)
        try:
            value = int(raw)                              # JSON strings no longer 500
        except (TypeError, ValueError):
            raise ValidationError('Prioridade inválida')
        if not MIN_PRIORITY <= value <= MAX_PRIORITY:
            raise ValidationError(f'Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}')
        return value
```

Keep the **exact original error messages and status codes** so clients do not break.

Serialization mirrors this: one `to_dict()` per model (§6), and computed fields
(`overdue`, `user_name`) become model methods or a presenter — never re-derived inline in three
different handlers.

**Check:** each rule's literal bounds appear once; `create` and `update` reject the same input;
grep for the old inline lists returns nothing.

---

## §15 — Replace deprecated APIs  (AP-M07)

Swap the call, keep the behaviour. Watch for semantic differences.

```python
# datetime.utcnow() returns a NAIVE datetime; the replacement is AWARE.
- created_at = datetime.utcnow()
+ created_at = datetime.now(timezone.utc)
```
Mixing aware and naive datetimes raises `TypeError`, so migrate **all** of them together —
column defaults, comparisons and serialization — or the `is_overdue` comparison will crash.

```python
# SQLAlchemy 2.0: Model.query and Query.get() are legacy
- user = User.query.get(user_id)
+ user = db.session.get(User, user_id)

- tasks = Task.query.filter_by(status='done').all()
+ tasks = db.session.scalars(select(Task).where(Task.status == 'done')).all()
```

```js
- const buf = new Buffer(input);              // DEP0005
+ const buf = Buffer.from(input);

- const parsed = url.parse(req.url);          // DEP0169
+ const parsed = new URL(req.url, `http://${req.headers.host}`);

- const cipher = crypto.createCipher(algo, password);      // DEP0106 — insecure key derivation
+ const cipher = crypto.createCipheriv(algo, key, iv);
```

**Check:** the deprecation sweep from the catalogue returns no hits; the app boots with
warnings-as-errors where practical (`python -W error::DeprecationWarning`, `node --pending-deprecation`).

---

## §16 — Readability pass  (AP-L02, AP-L04, AP-L06)

Do this last, once the structure is right — never mixed into a structural commit.

```js
- let u = req.body.usr, e = req.body.eml, p = req.body.pwd, cid = req.body.c_id, cc = req.body.card;
+ const { usr: name, eml: email, pwd: password, c_id: courseId, card } = req.body;
```
The wire format (`usr`, `eml`) stays — only the internal names improve, so no client breaks.

```python
- def is_admin(self):
-     if self.role == 'admin': return True
-     else: return False
+ def is_admin(self):
+     return self.role == 'admin'

- if type(tags) == list:
+ if isinstance(tags, list):

- print("Produto " + str(id) + " deletado")
+ logger.info("Produto %s deletado", produto_id)
```

Guard clauses replace nested pyramids:
```python
- if self.due_date:
-     if self.due_date < datetime.now(timezone.utc):
-         if self.status not in ('done', 'cancelled'):
-             return True
-         else: return False
-     else: return False
- else: return False
+ if not self.due_date or self.status in ('done', 'cancelled'):
+     return False
+ return self.due_date < datetime.now(timezone.utc)
```

**Check:** behaviour identical; the diff is renames and expression simplification only.

---

## Validation protocol (run after every refactor)

1. **Boot** — start the app with its documented command. Zero tracebacks, zero import errors.
2. **Route inventory** — diff the new route table against the baseline captured before the
   refactor. Every path/method present, none added silently.
3. **Endpoint sweep** — call every endpoint, including the failure cases (404, 400, 401).
   Compare status codes and response shapes to the baseline.
4. **Security re-check** — re-run the CRITICAL detection signals: no concatenated SQL, no
   secret literals, no credential fields in responses, no arbitrary-query route.
5. **Regression probes** — the injection payload that worked before now returns 401/400; the
   N+1 endpoint issues a constant number of queries.
6. Report only what you actually ran. If you could not boot the app, say so explicitly and list
   which checks were static-only.
