# Reference — Audit Report Template (Phase 2)

Print this to the terminal **and** write it to `reports/audit-<project-name>.md`.
The terminal version and the file version are the same document.

## Rules

- Findings sorted **CRITICAL → HIGH → MEDIUM → LOW**; within a severity, by file then line.
- Every finding cites `file:line` or `file:start-end`. No line number → not a finding.
- Finding IDs are sequential across the whole report: `F01`, `F02`, … Keep the catalogue ID
  (`AP-C03`) next to the name so the playbook lookup is unambiguous.
- Description says **what the code does**; Impact says **what it costs**; Recommendation says
  **the concrete transformation**, naming the playbook section.
- Aggregate repeated LOW findings into a single entry with a list of occurrences.
- The counts in Summary must equal the number of findings printed. Check before printing.

## Template

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <project-name>
Stack:   <language> + <framework version>
Files:   <N> analyzed | ~<L> lines of code
Date:    <YYYY-MM-DD>

## Summary

CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

<Two or three sentences: the headline architectural problem, the most urgent security issue,
and the shape of the recommended target structure.>

## Findings

### [CRITICAL] F01 — <Anti-pattern name> (<AP-ID>)
- **File:** `<path>:<line>` (add further `path:line` bullets when the same finding spans files)
- **Description:** <what the code actually does, quoting the offending expression>
- **Impact:** <concrete consequence — an exploit, a data-loss scenario, a maintenance cost>
- **Recommendation:** <the transformation, referencing playbook §N>

### [CRITICAL] F02 — ...

### [HIGH] F03 — ...

### [MEDIUM] F0n — ...

### [LOW] F0n — <Anti-pattern name> (<AP-ID>)
- **File:** `<path>:<line>`, `<path>:<line>`, `<path>:<line>` (aggregated — <k> occurrences)
- **Description:** ...
- **Impact:** ...
- **Recommendation:** ...

## Deprecated APIs

<A table of what the sweep found, or the single line "No deprecated APIs detected for this
stack." Never omit this section.>

| API | Location | Deprecated since | Replacement |
|---|---|---|---|
| `<api>` | `<file>:<line>` | <version> | `<replacement>` |

## Proposed Target Structure

```
<the MVC tree you will create in Phase 3>
```

## Migration Risk

<Anything that could change observable behaviour: endpoints you propose to remove, response
fields you propose to drop, a password re-hash that invalidates existing logins. Each item
must name the finding that justifies it. Write "none" when the refactor is fully
behaviour-preserving.>

================================
Total: <N> findings
================================
````

## Worked example of a single finding

```markdown
### [CRITICAL] F03 — SQL Injection via String Concatenation (AP-C03)
- **File:** `models.py:109-111`, `models.py:28`, `models.py:291`
- **Description:** `login_usuario()` builds its query by concatenation:
  `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`.
  `email` and `senha` come straight from the request body with no escaping. 14 further
  queries in this file are built the same way.
- **Impact:** Posting `{"email": "' OR '1'='1", "senha": "' OR '1'='1"}` to `/login`
  authenticates as the first user in the table — in the seed data, the admin. The same class
  of payload against `buscar_produtos` allows arbitrary reads via `UNION SELECT`.
- **Recommendation:** Replace every concatenated query with parameterized placeholders
  (`?`) and pass values as a tuple. Playbook §3.
```

## Terminal footer

After the report body, print exactly:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Then stop and wait for a human answer.
