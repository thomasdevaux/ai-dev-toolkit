---
name: ship-tool
description: Prepare a Python PC tool for shipping — lint, tests, and packaging are mandatory. Use when the user is finishing, releasing, or distributing a Python tool (not a throwaway script).
when_to_use: Use when asked to "finish", "ship", "release", or "package" a Python tool, or when the project already has a pyproject.toml.
---

# Ship a Python tool

Before considering a Python PC tool done, all of the following must pass:

1. **Lint**: `ruff check .` with zero unresolved issues.
2. **Format**: `ruff format --check .` clean (or run `ruff format .` and
   commit the result).
3. **Tests**: `pytest` passes. If there is no test suite yet and the tool
   has meaningful logic (not just argument parsing and I/O), add at least
   one test covering the main code path before shipping.
4. **Packaging**: a valid `pyproject.toml` with a `[build-system]` section
   and, if the tool has a CLI, a `[project.scripts]` entry point — see the
   Python packaging rule.
5. **Build check**: `python -m build` succeeds and produces a wheel without
   warnings about missing files.

Do not report the tool as "done" until all five checks pass — state which
ones you ran and their result.
