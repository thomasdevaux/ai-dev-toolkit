---
name: python-code-standards
description: Set up or repair the team's Python quality tooling in a project - ruff (format + lint), mypy, and the shared configuration they read. Use when a Python project has no ruff/mypy configuration, has one that diverges from the team's, when adopting the standards on an existing codebase with a backlog of findings, or when deciding whether a lint rule is worth turning on.
---

# Python Code Standards

Install the team's Python quality configuration in a project, or bring an
existing one back in line. The day-to-day rules — run the tools, how to
silence a finding legitimately — live in `rules/style.md` and load on their
own; this skill is the setup procedure.

## The stack, and why

| Job | Tool |
|---|---|
| Format | `ruff format` |
| Lint | `ruff check` |
| Types | `mypy` |

**One linter, not a stack of plugins.** Ruff implements the rule sets of
flake8 and its plugin ecosystem, black, isort and pyupgrade in a single
binary, configured in one place. A project that still runs black + isort +
flake8 separately is maintaining four configurations that can disagree with
each other.

**`ty` is not the default yet.** Astral's type checker is far faster than
mypy and was still beta as of 2026-08-07, with 1.0 targeted for later in the
year. Use it if the project's owner wants the speed and accepts beta
software; the configuration below stays valid either way, since both read
the same annotations.

**`uv` for environments** if the project has a choice. It is out of scope
here — this skill configures quality tooling, not packaging — but it is what
the reference `pyproject.toml` assumes when it says "install the dev
dependencies".

## Procedure

### A project with no configuration

1. Read `references/pyproject-quality.toml`. Merge its sections into the
   project's `pyproject.toml`. Do not copy the file to the project root as
   a whole — it is a fragment, and a Python project already has a
   `pyproject.toml` to receive it.
2. Set `target-version` (ruff) and `python_version` (mypy) to the oldest
   interpreter the project actually supports. Both default to `py312` in the
   reference; a project on 3.11 that leaves them will get suggestions it
   cannot apply.
3. Add `ruff` and `mypy` to the project's dev dependencies.
4. Copy `references/editorconfig.ini` to the project root as `.editorconfig`
   if there is none. It is the same baseline in every stack and settles what
   an editor decides before any formatter runs.
5. Run `ruff format` then `ruff check --fix`, and commit that as one
   mechanical commit, separate from any behaviour change. A formatting
   commit mixed into a feature commit makes the feature unreviewable.
6. Run `mypy` and deal with the output per the section below.

### A project that already has a configuration

Do not overwrite it. Diff it against the reference and report the
differences, grouped:

- **Rules the project disables that the reference enables** — ask why before
  removing the exception. A project silencing `S` (bandit) wholesale usually
  has a reason worth writing down instead.
- **Rules the project enables that the reference does not** — a candidate to
  propose upstream, not to delete.
- **`line-length`, `target-version`, `python_version`** — align on the
  reference unless the project has a stated reason.

Bring the project to the reference where there is no reason to differ, and
record the deliberate differences as comments in its own config next to the
setting.

### Adopting on an existing codebase with a large backlog

The failure mode is a first run reporting several hundred findings, which
gets ignored wholesale and the standard dies on day one. Instead:

1. Land the formatter first, alone. `ruff format` across the repo is
   mechanical and reviewable as a single commit.
2. Enable lint rule groups in order of value: `F` and `B` first (real bugs),
   then `E`/`W`/`I`/`UP`, then the rest. One group per commit, each one
   clean before the next.
3. For mypy, start from the reference's non-strict settings. Tighten toward
   `strict = true` only once the baseline is clean.
4. Never adopt a standard by adding a repo-wide `# type: ignore` or a broad
   `per-file-ignores` covering the whole source tree — that records the
   backlog as permanent.

## Changing the standard

The reference configuration is the team's, not the project's. A rule worth
enabling or disabling everywhere is changed in
`tech-stacks/python/skills/python-code-standards/references/` in the toolkit
checkout, and reaches projects at their next sync. Editing one project's
config to win an argument is how four projects end up with four standards.
