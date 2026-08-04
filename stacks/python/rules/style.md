---
paths:
  - "**/*.py"
---

# Python style

- Format with `ruff format` and lint with `ruff check` before committing;
  fix or explicitly justify every reported issue.
- Type-annotate function signatures for any code shared across files (not
  required for a single throwaway script).
- Use `pathlib.Path` instead of raw string path manipulation.
- Prefer f-strings over `%` or `.format()` for string interpolation.
- No bare `except:` — catch specific exceptions, or `except Exception` with
  a comment explaining why broader is needed.
- Keep functions under ~50 lines; extract a helper when a function does
  more than one thing.
