# Reference — Target MVC Architecture (Phase 3)

The target is MVC with an explicit composition root. The *names* below are canonical; adapt the
file extensions and module conventions to the detected language, but keep the layer boundaries
identical across stacks.

## The dependency rule

```
routes/views  →  controllers  →  models  →  database
      ↘              ↓             ↙
            config  ·  middlewares  ·  utils
```

Dependencies point **inward and downward only**.

- A **route** may import controllers. It may not import models or the database.
- A **controller** may import models, config and utils. It may not import the HTTP router.
- A **model** may import the database and config. It may not import controllers or routes,
  and it may not perform I/O other than persistence.
- Nothing imports the composition root.

If a file needs an upward import, the layering is wrong — move the code, do not add the import.

## Layers

### `config/` — configuration
- All environment-dependent values: secrets, connection strings, ports, feature flags, limits.
- Read from environment variables with safe non-production defaults so the app still boots
  locally without setup. Ship a `.env.example` listing every variable.
- **No secret literals.** A default may exist for a dev-only value (`sqlite:///app.db`), never
  for a real credential.
- Domain constants that are policy rather than environment (valid statuses, price tiers,
  length bounds) live here or in a `constants` module — never inline in a handler.

### `models/` — data and domain state
- One module per aggregate/entity (`produto_model.py`, `Course.js`), named after the domain.
- Owns: table/schema definition, all queries for that entity, and the mapping between rows and
  domain objects.
- **All SQL lives here**, always parameterized. No query strings anywhere else in the tree.
- Owns entity-local invariants (`is_overdue()`, `can_transition_to(status)`).
- Does **not**: read the HTTP request, build HTTP responses, send email, log business events,
  or know that a web framework exists.

### `controllers/` — application flow
- One module per domain area, mirroring the models (`pedido_controller`, `checkout_controller`).
- Owns: input validation, orchestration across models, transaction boundaries, authorization
  decisions, and mapping domain results to a response payload.
- This is where a use case lives end to end: validate → load → decide → persist → serialize.
- Raises typed domain errors (`NotFoundError`, `ValidationError`, `ConflictError`) instead of
  building 404/400 responses by hand — the error middleware turns them into HTTP.
- Does **not**: contain SQL, or reach into another domain's tables directly.

### `views/` or `routes/` — HTTP surface
- Pure wiring: method + path + middleware + the controller function that handles it.
- A route body should be one line. If it has branching, the branch belongs in a controller.
- Keep every original path, method and parameter name **exactly** as it was.
- Group by resource (`produto_routes`, `checkout_routes`), and register them in one place.

### `middlewares/` — cross-cutting concerns
- Centralized error handler: one place that maps domain errors and unexpected exceptions to
  HTTP status + a consistent body, logs the real error server-side, and never returns a stack
  trace or an exception message to the client.
- Also: request logging, auth guards, CORS policy, body-size limits, 404 handler.
- Every handler is registered by the composition root, never scattered.

### `services/` — optional, for genuine external integrations
Only create this when the project talks to something outside itself (SMTP, a payment gateway,
an object store). A service wraps *one* external system behind an interface the controller can
fake in a test. Business logic does not live here — that is the controller's job.

### `utils/` — leaf helpers only
Pure functions with no state and no imports from other layers (date formatting, percentage
maths, string sanitizing). If a "util" needs the database, it is a model. If it needs the
request, it is a controller or a middleware.

### Composition root — `app.py` / `src/app.js`
The only file that knows how the pieces fit:
1. load config
2. create the app/framework instance
3. create the database connection/session
4. instantiate models/services and inject them into controllers
5. register middlewares, then routes
6. register the error handler **last**
7. expose the app; start the server only under the `__main__` / start-script guard

Nothing else instantiates a connection or reads an environment variable.

## Reference trees

**Python / Flask**
```
src/
├── config/
│   ├── __init__.py
│   └── settings.py
├── models/
│   ├── __init__.py
│   └── produto_model.py
├── controllers/
│   ├── __init__.py
│   └── produto_controller.py
├── views/
│   ├── __init__.py
│   └── produto_routes.py         # Blueprint
├── middlewares/
│   ├── __init__.py
│   └── error_handler.py
├── utils/
│   └── validators.py
└── app.py                        # create_app() factory + composition root
```

**Node.js / Express**
```
src/
├── config/index.js
├── models/CourseModel.js
├── controllers/CheckoutController.js
├── routes/checkoutRoutes.js      # express.Router()
├── middlewares/errorHandler.js
├── errors/AppError.js
├── utils/logger.js
└── app.js                        # buildApp() + server bootstrap
```

Use the framework's own layering primitive for the routes layer — Flask `Blueprint`,
Express `Router`, NestJS module, Rails controller. Do not hand-roll a dispatcher.

## When the project is already partly layered

Do not flatten and rebuild. Audit each existing directory against the dependency rule and move
only what violates it:
- `routes/` files containing queries → extract a `controllers/` layer beneath them.
- `models/` performing I/O → move the I/O into a `services/` wrapper called by the controller.
- `utils/` holding validation used by one domain → move it to that domain's controller/validator.
- Directories that already comply → leave untouched.

## Definition of done

- [ ] No SQL or ORM query outside `models/`
- [ ] No `request`/`req`/`res` object outside `views|routes/`, `controllers/`, `middlewares/`
- [ ] No secret literal anywhere; every secret read from config
- [ ] Exactly one error-handling registration; no per-handler `try/except → 500`
- [ ] Every original route present with its original method, path and status codes
- [ ] The composition root is the only file wiring dependencies together
- [ ] The app boots and every endpoint answers
