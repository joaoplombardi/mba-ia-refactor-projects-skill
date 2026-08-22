# Reference — Anti-Pattern Catalog (Phase 2)

Each entry gives **detection signals** (what to grep / what to look at) and the **severity** it
carries. Signals are candidates; confirm by reading the surrounding code before you report.

## Severity rules

| Severity | Meaning |
|---|---|
| **CRITICAL** | Breaks correctness or security, exposes sensitive data, or collapses all responsibilities into one unit. Exploitable or data-losing. |
| **HIGH** | Strong MVC/SOLID violation that makes the code untestable or unmaintainable: business logic trapped in controllers, hard coupling with no injection, mutable global state. |
| **MEDIUM** | Standardisation, duplication, or moderate performance problems: N+1 queries, missing validation, scattered error handling, deprecated APIs. |
| **LOW** | Readability: naming, magic numbers, redundant conditionals, `print` as logging. |

Escalation rules that override the table:
- Any severity **+1** when the code path handles authentication, payment, or personal data.
- Duplication **+1** to HIGH when the duplicated block is a *validation rule* — divergence
  between copies becomes a correctness bug.
- A LOW pattern repeated more than ~10 times is reported **once**, aggregated, at MEDIUM.

---

## CRITICAL

### AP-C01 — God Class / God Module
One file (or class) owns routing **and** persistence **and** business rules **and** formatting.
- Signals: a single file over ~150 lines matching `route|app\.(get|post|put|delete)|add_url_rule`
  *and* `execute|db\.run|db\.all|session\.` *and* domain arithmetic; a class named
  `*Manager`, `*Helper`, `*Util`, `*Service` that does everything; `setupRoutes(app)` methods.
- Impact: nothing can be unit-tested in isolation; every change is a wide blast radius.
- Fix: playbook §1.

### AP-C02 — Hardcoded Credentials / Secrets
- Signals: `SECRET_KEY\s*=`, `password|passwd|pwd|senha\s*[=:]`, `api[_-]?key`, `token\s*=`,
  `pk_live_`, `sk_live_`, `AKIA[0-9A-Z]{16}`, SMTP user/password literals, DB user/password
  literals, connection strings with inline credentials.
- Impact: secret is in git history forever; rotation requires a code change and redeploy.
- Fix: playbook §2.

### AP-C03 — SQL Injection via String Concatenation
- Signals: SQL keywords adjacent to `+`, `%`, f-strings or template literals —
  `"SELECT .*" *\+`, `f"...WHERE.*{`, `` `...WHERE ${ ``, `.format(` on a query string,
  `"%s" %` on a query. Any user-controlled value reaching `execute()` without a placeholder.
- Impact: authentication bypass, data exfiltration, data destruction. A login query built by
  concatenation is trivially bypassable with `' OR '1'='1`.
- Fix: playbook §3.

### AP-C04 — Arbitrary Query / Code Execution Endpoint
A route that takes SQL, a shell command, or code from the request body and runs it.
- Signals: a handler reading `sql`, `query`, `cmd`, `code` from the body and passing it to
  `execute`, `eval`, `exec`, `system`, `child_process`.
- Impact: full remote database or host takeover. Nothing else in the audit matters more.
- Fix: playbook §4 — delete the endpoint.

### AP-C05 — Broken or Absent Password Storage
- Signals: passwords stored as received; `hashlib.md5`, `hashlib.sha1`, `crypto.createHash('md5')`;
  hand-rolled hash functions (loops concatenating `base64`/`substring`); comparison of a stored
  password with `==` on a plaintext value; `check_password` that re-hashes with a fast digest.
- Impact: a database leak becomes a credential leak. MD5/SHA-1 are not password hashes — they
  are fast and unsalted, so they are brute-forced offline in minutes.
- Fix: playbook §5.

### AP-C06 — Sensitive Data Leaked in Responses
- Signals: `password|senha|pass|token|secret` present in a serializer / `to_dict` / `SELECT *`
  that feeds a response; a health or debug endpoint echoing config; user listings returning
  credential columns.
- Impact: silent credential disclosure to any caller.
- Fix: playbook §6.

### AP-C07 — Unauthenticated Destructive Endpoint
- Signals: `DELETE`/`POST` routes named `reset`, `drop`, `truncate`, `purge`, `admin/*`, with no
  auth check anywhere in the handler or middleware chain; `DELETE FROM <table>` without a `WHERE`.
- Impact: any anonymous caller can wipe production data.
- Fix: playbook §4.

### AP-C08 — Missing Transaction Boundary on Multi-Step Writes
A business operation writes several tables with no transaction, so a mid-way failure leaves
partial state. Also: deleting a parent row without handling children (orphan rows).
- Signals: two or more `INSERT`/`UPDATE`/`DELETE` in one handler with a single trailing commit
  and no rollback path; nested callbacks each writing; `DELETE FROM users` with no cascade or
  cleanup of dependent tables; a comment admitting the leftovers.
- Impact: money taken with no enrolment recorded; stock decremented for an order that failed;
  permanently inconsistent data.
- Fix: playbook §8.

---

## HIGH

### AP-H01 — Fat Controller / Business Logic in the Route Handler
- Signals: a route handler over ~30 lines; validation, computation, persistence and
  serialization inside one function; the framework's `request`/`res` object referenced in the
  middle of domain arithmetic.
- Impact: the rule cannot be tested or reused without an HTTP request; the same rule gets
  copy-pasted into the next handler.
- Fix: playbook §1 and §7.

### AP-H02 — Missing Controller Layer (routes call persistence directly)
Routes reach into the ORM/SQL with no orchestration layer in between.
- Signals: `.query.`, `session.add`, `cursor.execute`, `db.all(` inside a file under
  `routes/`, `views/`, or inside a `@app.route`-decorated function.
- Impact: no seam for transactions, authorization or reuse; the HTTP layer owns the domain.
- Fix: playbook §7.

### AP-H03 — Mutable Global State / Module-Level Singleton
- Signals: module-level `global` declarations, a module-scope mutable dict/list used as a
  cache (`globalCache = {}`, `totalRevenue = 0`), a lazily-created global connection
  (`if db_connection is None: db_connection = ...`), `check_same_thread=False`.
- Impact: not thread-safe, not testable (state leaks across tests), unbounded memory growth,
  impossible to run more than one instance correctly.
- Fix: playbook §9.

### AP-H04 — Hardcoded Dependencies / No Dependency Injection
A unit constructs its own collaborators, so it cannot be tested with fakes.
- Signals: `new Sqlite3.Database(...)` inside a constructor; `get_db()` called deep inside a
  model function; a service instantiating its own SMTP client; direct `import`-and-call of a
  concrete module where an interface belongs.
- Impact: tests hit the real database and the real SMTP server; swapping implementations means
  editing every call site.
- Fix: playbook §9.

### AP-H05 — Side Effects in the Model / Data Layer
Notifications, emails, logging or HTTP calls performed from the persistence or domain layer.
- Signals: `smtplib`, `sendmail`, `fetch(`, `requests.`, `print(`/`console.log` of business
  events inside model or repository code; a "send email" call in the middle of a save.
- Impact: saving a row sends an email; the model can never run offline or in a test.
- Fix: playbook §10.

### AP-H06 — Callback Pyramid / Manual Async Orchestration
Deeply nested callbacks, hand-rolled pending counters, or a response sent from several places
in the same handler.
- Signals: 3+ levels of `function(err, ...)` nesting; `let pending = xs.length; pending--` with
  `if (pending === 0) res.json(...)`; `forEach` containing async calls; `err` parameters
  received and ignored.
- Impact: unreachable error paths, double `res.send` crashes, race conditions, results in
  nondeterministic order.
- Fix: playbook §11.

### AP-H07 — Insecure Defaults Left On
- Signals: `debug=True`, `DEBUG: True`, `app.run(debug=True)`, `NODE_ENV` never checked,
  `CORS(app)` with no origin restriction, `cors({origin: '*'})`, stack traces returned to the
  client (`return str(e)` in a 500 body), verbose SQL logging.
- Impact: Flask's debug console is remote code execution when reachable; error bodies leak
  internal paths and schema.
- Fix: playbook §2 and §12.

---

## MEDIUM

### AP-M01 — N+1 Query
A query executed once per row of a previous result.
- Signals: `execute`/`query`/`.get(` inside a `for`/`forEach`/list comprehension; a nested loop
  where the inner body queries by the outer row's id; ORM relationship access inside a loop
  with no eager loading (`joinedload`, `selectinload`, `include`).
- Impact: 1 + N (or 1 + N×M) round trips; latency grows linearly with data.
- Fix: playbook §13.

### AP-M02 — Duplicated Validation Logic
The same rule written in more than one place.
- Signals: identical literal bounds repeated (`len(title) < 3`, `priority < 1 or priority > 5`);
  the same allowed-values list inline in several files; a `create` handler and an `update`
  handler validating the same field independently; a shared helper that exists but is unused.
- Impact: rules drift — `create` rejects what `update` accepts.
- Fix: playbook §14.

### AP-M03 — Duplicated / Manual Serialization
Hand-built response dicts repeated per handler, or a `to_dict` that exists but is bypassed.
- Signals: the same key list assembled in several functions; `data['x'] = obj.x` chains; a
  model with `to_dict()` alongside handlers that build the dict inline.
- Impact: adding a field means editing N places; responses diverge between endpoints.
- Fix: playbook §6 and §14.

### AP-M04 — Scattered Error Handling
Every handler repeats the same `try/except → 500` block instead of one centralized handler.
- Signals: `except Exception as e: return ... 500` repeated across handlers;
  `if (err) return res.status(500).send(...)` at every callback; no `@app.errorhandler`,
  no Express error middleware `(err, req, res, next)`.
- Impact: inconsistent error shapes, duplicated code, and inevitably a path where the error is
  swallowed.
- Fix: playbook §12.

### AP-M05 — Swallowed Exceptions / Bare Catch
- Signals: `except:` with no exception type, `except Exception: pass`, `catch (e) {}`,
  `try/except` wrapping a whole handler and returning a generic message, callbacks that accept
  `err` and never test it.
- Impact: real failures become silent wrong answers; debugging is guesswork.
- Fix: playbook §12.

### AP-M06 — Missing or Late Input Validation
- Signals: `request.get_json()` / `req.body` fields used with no presence or type check;
  numeric fields compared without a cast (`priority < 1` on a string from JSON);
  a route that validates on `create` but not on `update`; no validation layer at all.
- Impact: 500s instead of 400s; type errors reaching the database; corrupt rows.
- Fix: playbook §14.

### AP-M07 — Deprecated / Legacy API Usage
Run this sweep every audit, against the stack detected in Phase 1. Report only what is
**actually present** — and cite the replacement.

**Python**
| Deprecated | Since | Replacement |
|---|---|---|
| `datetime.utcnow()`, `datetime.utcfromtimestamp()` | Python 3.12 | `datetime.now(timezone.utc)` |
| `Model.query` / `Query.get(pk)` (SQLAlchemy legacy) | SQLAlchemy 2.0 | `db.session.get(Model, pk)`, `db.session.execute(select(...))` |
| `@app.before_first_request` | removed in Flask 2.3 | app-factory setup or `with app.app_context()` |
| `flask.json.JSONEncoder` | removed in Flask 2.3 | `app.json_provider_class` |
| `werkzeug.urls.url_encode/url_parse` | removed in Werkzeug 2.4 | `urllib.parse` |
| `imp`, `distutils` | removed in 3.12 | `importlib`, `packaging`/`setuptools` |
| `pkg_resources` | deprecated | `importlib.metadata` |

**Node.js**
| Deprecated | Since | Replacement |
|---|---|---|
| `new Buffer()` / `Buffer(size)` | Node 6 (DEP0005) | `Buffer.from()` / `Buffer.alloc()` |
| `url.parse()` | Node 11 (DEP0169) | `new URL()` |
| `crypto.createCipher` / `createDecipher` | Node 10 (DEP0106) | `createCipheriv` / `createDecipheriv` |
| `util.isArray`, `util._extend` | Node 4 / 6 | `Array.isArray`, object spread |
| `domain` module | Node 4 | `AsyncLocalStorage` |
| `fs.exists` | Node 1 (DEP0018) | `fs.access` / `fs.promises.access` |
| `process.binding` | Node 10 (DEP0111) | public APIs |
| `sqlite3` `.verbose()` in production | — | drop it, or use the promise wrapper |
| Express 4 `res.send(status)`, `app.del()` | Express 4 | `res.sendStatus(status)`, `app.delete()` |
| Callback-only DB APIs where a promise API ships | — | `util.promisify` / the library's promise build |

Severity: MEDIUM by default. Escalate to HIGH when the API is **removed** in a version the
manifest already allows (the app is one `pip install -U` from breaking), or when the deprecated
call is in a security path (`createCipher`, an MD5 digest of a password).

### AP-M08 — Dead Code / Unused Imports
- Signals: imports never referenced (`import os, sys, json` in a file using none of them),
  exported symbols never imported anywhere (`totalRevenue`), functions with no call sites,
  commented-out blocks.
- Impact: misleads readers about dependencies; hides what the module actually needs.
- Fix: delete.

---

## LOW

### AP-L01 — Magic Numbers and Magic Strings
- Signals: bare numeric literals in rules (`> 10000`, `* 0.1`, `< 3`, `> 200`); status/role
  strings repeated inline (`'pending'`, `'admin'`, `'PAID'`); ports, timeouts and limits inline.
- Fix: named constants or an enum, in the config or domain module. Aggregate into one finding.

### AP-L02 — Poor Naming
- Signals: single- or two-letter identifiers for domain values (`u`, `e`, `p`, `cc`, `cid`, `t`,
  `c`); body keys abbreviated beyond recognition (`usr`, `eml`, `pwd`, `c_id`); names that lie
  (`utils.js` holding config and crypto; a `models` module holding controllers); `data`,
  `result`, `temp` for domain concepts.
- Fix: rename to the domain vocabulary. Keep the wire format unchanged unless the audit says
  otherwise.

### AP-L03 — `print` / `console.log` as Logging
- Signals: `print(` / `console.log(` used for operational events, string-concatenated messages,
  no levels, no timestamps, logging of request payloads (often including card numbers or
  passwords — that instance is CRITICAL under AP-C06, not LOW).
- Fix: the standard logger with levels; playbook §12.

### AP-L04 — Redundant Conditionals / Nested If Pyramids
- Signals: `if cond: return True else: return False`; three or more nested `if`s that compute a
  single boolean; `if x == True`; `type(x) == list` instead of `isinstance`.
- Fix: return the expression; use guard clauses.

### AP-L05 — Inconsistent Response Contract
- Signals: some endpoints return `{"dados": ..., "sucesso": true}` and others return a bare
  array or a plain string; error bodies sometimes `{"erro": ...}`, sometimes `{"error": ...}`,
  sometimes `res.send("Bad Request")`; inconsistent status codes for the same class of failure.
- Impact: every client needs per-endpoint special cases.
- Fix: one response envelope helper — but **preserve each endpoint's existing shape** during the
  refactor unless the user approves an API change.

### AP-L06 — String Concatenation for Message Building
- Signals: `"text " + str(x) + " more"` in Python where an f-string reads better; `+` chains
  in JS where a template literal fits.
- Fix: f-strings / template literals. Aggregate into one finding.
