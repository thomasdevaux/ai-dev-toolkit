---
paths:
  - "**/*.py"
---

# Python code standards

The mechanical part is enforced by tooling, not by this file: `ruff format`
and `ruff check` for style and lint, `mypy` for types. Their configuration is
the actual standard — `python-code-standards` holds the ready-to-copy version
and the procedure for adopting it. If a project has no such configuration
yet, say so once and offer to run that skill; don't hand-apply preferences a
linter should own.

What tooling cannot decide, and this file does:

- **Run the tools before handing work back.** `ruff format`, then
  `ruff check`, then `mypy` on what you touched. A finding is either fixed or
  silenced with a reason — never left reported and ignored.
- **Silencing needs a named rule and a why.** `# noqa: E501` alone is not
  acceptable; `# noqa: E501 - URL, cannot wrap` is. Bare `# noqa` and
  blanket `# type: ignore` are never acceptable — they suppress findings
  nobody chose to accept.
- **Type-annotate anything crossing a module boundary.** A function another
  file imports is annotated. A local helper inside one module is not
  required to be, and a throwaway script is not either.
- **Catch specific exceptions.** `except Exception` is allowed where a
  boundary genuinely must not let anything through — a request handler, a
  worker loop — and carries a comment saying so. Bare `except:` is not.
- **Errors carry context or they are not caught.** Re-raising with `raise
  ... from err` keeps the chain; swallowing an exception to return `None`
  loses the reason and hides the bug.
- **Prefer the standard library's own answer** before a dependency:
  `pathlib` over string path arithmetic, `dataclasses` over hand-written
  `__init__`, f-strings over `%` and `.format()`.

Adding a lint rule to the shared configuration is a team decision, not a
per-project one: propose it against the toolkit's `python-code-standards`
reference rather than editing one project's config alone.
