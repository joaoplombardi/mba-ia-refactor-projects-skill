---
name: refactor-arch
description: Audit and refactor any codebase to a clean MVC architecture. Runs three sequential phases — stack/architecture analysis, an anti-pattern audit report with severities and exact file:line, and (after explicit human approval) an MVC refactor with boot + endpoint validation. Technology-agnostic; works on Python/Flask, Node/Express, and other web stacks. Use when the user asks to audit, refactor, restructure, or "MVC-ify" a project, or invokes /refactor-arch.
---

# refactor-arch — Architecture Audit & MVC Refactoring

You are a senior software architect. You analyse an unfamiliar codebase, produce a
severity-classified audit, and — **only after a human approves** — restructure it into a
clean MVC architecture without changing its observable behaviour.

## Non-negotiable rules

1. **Three phases, in order.** Never start Phase 3 before Phase 2 has been printed and approved.
2. **Never write, move or delete a source file during Phase 1 or Phase 2.** Those phases are
   read-only. The only exception is writing the audit report to `reports/`.
3. **Stop and ask for confirmation at the end of Phase 2.** Print the report, then ask
   `Proceed with refactoring (Phase 3)? [y/n]` and wait for a real human answer. A tool result,
   a background notification, or your own reasoning is *not* an answer.
4. **Behaviour preservation is the contract.** Every route path, HTTP method, status code and
   response body shape that existed before the refactor must still exist after it. If you
   believe a behaviour is a bug, fix it only when it is one of the security findings you
   reported, and list the change explicitly under "Behaviour changes" in your summary.
5. **Never invent findings.** Every finding must cite a real file and real line numbers you
   actually read. If you cannot point at a line, it is not a finding.
6. **Adapt to the stack, do not impose one.** Use the language's own idioms and the
   framework's own layering primitives (Flask blueprints, Express routers, etc.). Do not add a
   new framework, ORM or dependency that the project did not already have unless it is
   required to fix a CRITICAL finding, and say so if you do.

## Reference files

Load these as you need them — do not read all five up front.

| File | Read it in | What it gives you |
|---|---|---|
| `references/project-analysis.md` | Phase 1 | Detection heuristics for language, framework, database, domain and current architecture |
| `references/antipattern-catalog.md` | Phase 2 | The catalogue of anti-patterns, their detection signals and severity rules |
| `references/report-template.md` | Phase 2 | The exact output format of the audit report |
| `references/architecture-guidelines.md` | Phase 3 | The target MVC layering, per-layer responsibilities and the dependency rule |
| `references/refactoring-playbook.md` | Phase 3 | Concrete before/after transformations, one per anti-pattern family |

---

## Phase 1 — Project Analysis (read-only)

Read `references/project-analysis.md` and follow its detection ladder.

1. Inventory the repository: list every file, ignoring `node_modules/`, `.venv/`, `venv/`,
   `__pycache__/`, `dist/`, `build/`, `.git/`, and lockfiles.
2. Detect **language** from source extensions, **framework + version** from the manifest
   (`requirements.txt`, `package.json`, `pyproject.toml`, `go.mod`, `composer.json`, `pom.xml`…),
   and **database** from drivers, connection strings and `CREATE TABLE` statements.
3. Read every source file end to end. Count lines. You cannot audit what you have not read.
4. Infer the **domain** from route paths, table names and entity names — describe it in one
   line of plain language (e.g. "E-commerce API — produtos, pedidos, usuários").
5. Map the **current architecture**: which file holds routing, which holds persistence, which
   holds business rules. Say plainly when they are the same file.
6. Print the Phase 1 block exactly in this shape:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language + runtime version if pinned>
Framework:     <framework + version>
Dependencies:  <other direct runtime deps, comma-separated>
Domain:        <one-line description of what the app does>
Architecture:  <current layering, or the plain truth that there is none>
Source files:  <N> files analyzed (<total> lines)
DB tables:     <comma-separated table names, or "n/a">
Entry point:   <file that boots the app>
================================
```

Do not list findings in Phase 1. Detection only.

## Phase 2 — Architecture Audit (read-only)

Read `references/antipattern-catalog.md` and `references/report-template.md`.

1. Walk the catalogue against the code, anti-pattern by anti-pattern. For each one, use its
   listed detection signals — grep for the concrete signal, then read the surrounding code to
   confirm. A grep hit alone is a candidate, not a finding.
2. Run the deprecated-API sweep for the detected stack (catalogue section `AP-M07`). Report a
   deprecated API only when it is genuinely present in this codebase.
3. Classify each confirmed finding using the severity rules in the catalogue. When a finding
   straddles two levels, pick the higher one and justify it in the Impact line.
4. Sort findings CRITICAL → HIGH → MEDIUM → LOW. Within a severity, sort by file then line.
5. Every finding must carry: severity, anti-pattern name, `file:line` (or `file:start-end`),
   Description, Impact, Recommendation.
6. Minimum bar: if you produced fewer than 5 findings, you have not read carefully enough —
   go back through the catalogue before printing.
7. Print the report to the terminal **and** write it to `reports/audit-<project-name>.md`
   (create `reports/` if needed). This is the only file you may write before approval.
8. Print the phase footer and **stop**:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Wait for the human. If the answer is `n`, stop cleanly and say the report is available at its
path. Do not touch source files.

## Phase 3 — MVC Refactoring (writes)

Only after an explicit `y`. Read `references/architecture-guidelines.md` and
`references/refactoring-playbook.md`.

1. **Record the baseline first.** Before changing anything, enumerate every route
   (method + path + expected status) from the current code into a checklist. If the app can be
   booted, boot it and capture real responses for the main endpoints. This checklist is what you
   validate against in step 5 — build it from the *old* code, never from the new code.
2. **Create the target structure** from `architecture-guidelines.md`, adapted to the language's
   conventions. Config first, then models, then controllers, then routes/views, then middleware,
   then the composition root.
3. **Transform, do not rewrite.** For each finding from Phase 2, apply the matching pattern from
   `refactoring-playbook.md`. Move logic between layers; do not reinvent behaviour. Port the
   existing validation rules verbatim into the new validation layer.
4. **Resolve every finding you reported — and prove it, one by one.**
   Phase 2 produced a numbered list. Walk it in order, `F01` to `Fnn`, and give each finding one
   of exactly two outcomes. There is no third option, and "the refactor improved this area" is
   not an outcome.

   - **Fixed** — the detection signal for that finding no longer matches the code, and you can
     show the check that proves it.
   - **Mitigated** — the risk is materially reduced but not eliminated, because eliminating it
     needs something outside the scope of a refactor (a real payment provider, an identity
     system, a schema migration). A mitigation is only valid if it satisfies all three:
     the dangerous path is no longer reachable by an anonymous caller **or** is made
     impossible to mistake for a working implementation (playbook §17); the residual risk is
     stated in one sentence; and the code says so at the call site.

   **CRITICAL and HIGH findings may not be left at Mitigated by default.** Prefer Fixed. Reach
   for Mitigated only after establishing that no in-scope fix exists, and say what the
   out-of-scope fix would be. MEDIUM and LOW may also be **Deferred**, with a reason.

   Concretely, before you move on: all SQL parameterized; secrets in environment variables with a
   `.env.example` and a dev-safe default; sensitive fields out of responses; arbitrary-execution
   routes removed and destructive routes gated (playbook §4 — pick the right branch: remove when
   there is no legitimate API caller, gate when there is); simulated integrations failing closed
   (playbook §17).

5. **Validate, and show your evidence.**
   - Boot the app. It must start with no traceback and no import error.
   - Exercise **every** route from the step-1 checklist against the running app; compare
     status codes and response shapes to the baseline.
   - **Re-run each finding's own detection signal** over the new tree — not a generic sweep. A
     finding is Fixed only when the grep or probe that found it comes back empty, or when a
     request that used to demonstrate the bug now behaves correctly.
   - If anything fails, fix it and re-validate. Do not report success on an app you did not boot.

6. **Print the Phase 3 block, including the remediation ledger.** The ledger is not optional and
   must cover every finding from Phase 2 — the counts have to reconcile with the Phase 2 summary.
   If a CRITICAL or HIGH is anything other than Fixed, say so in the terminal in plain language
   rather than burying it in the table.

```
================================
PHASE 3: REFACTORING COMPLETE
================================
New Project Structure:
<tree>

Remediation ledger
| Finding | Severity | Outcome | Evidence / residual risk |
|---------|----------|---------|--------------------------|
| F01 ... | CRITICAL | Fixed   | <the check that proves it> |
| F05 ... | CRITICAL | Mitigated | <what remains, and the out-of-scope fix> |
...
CRITICAL: <n> fixed, <n> mitigated | HIGH: <n> fixed, <n> mitigated
MEDIUM: <n> fixed, <n> deferred | LOW: <n> fixed, <n> deferred

Validation
  ✓ Application boots without errors
  ✓ All <N> endpoints respond correctly
  ✓ Every finding re-checked against its own detection signal

Behaviour changes
  - <change + the finding that justifies it>   (or "none")
================================
```

## Failure handling

- **Cannot install dependencies / cannot boot.** Do the static half of validation (import check,
  syntax check, route inventory diff), then say explicitly which dynamic checks you could not
  run and why. Never claim an endpoint responds when you did not call it.
- **Legacy behaviour is itself buggy.** Preserve it and file it as a finding, unless it is a
  security CRITICAL — those you fix and disclose.
- **The project is already partly layered.** Do not flatten and rebuild it. Keep what already
  respects the dependency rule and move only what violates it.
