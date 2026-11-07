# Build configuration and disk

What the environment side of a Python project pins, and why it needs no cap
script like Rust's. The settings go in files the project already has.

## What gets pinned

| Setting | Where | What it settles |
|---|---|---|
| the interpreter's minor (`3.12`) | `.python-version` | the one Python uv creates `.venv` with, on every machine |
| `requires-python = ">=3.12"` | `pyproject.toml` | the oldest interpreter the project accepts |
| `target-version` (ruff), `python_version` (mypy) | `pyproject.toml` | which syntax the linter suggests and the type checker accepts |
| every dependency, transitive ones included | `uv.lock`, committed | one environment across machines and over time |
| `ruff`, `mypy`, `pytest`, `pyinstaller` | the `dev` dependency group | the tools themselves, locked like the rest |

The four interpreter settings name the same minor and move together, in their
own commit. For a desktop app, that minor is one PySide6 and PyInstaller both
support — not the newest Python by reflex.

**`uv sync --locked`, not `uv sync`.** Without `--locked`, uv rewrites
`uv.lock` whenever `pyproject.toml` changed; with it, a lockfile out of step
fails instead. That is the first step of the desktop gate, and the one a
build script runs before PyInstaller.

**Upgrading**: `uv lock --upgrade-package <name>` for one dependency, `uv lock
--upgrade` for all, each in its own commit. Read the `uv.lock` diff: it is the
only place a transitive upgrade shows up.

## Release builds

A desktop app builds with PyInstaller into `dist/release/` and `dist/debug/`,
intermediate files in `.build/` (`python-desktop-architecture`, its
reference's §4). `uv init --package` gitignores `dist/` already; add `.build/`.

## Versioned or machine-local

Shared settings are versioned in the project. What belongs to one machine only
stays out of it, in the user environment or `%APPDATA%\uv\uv.toml`:

- `UV_DEFAULT_INDEX` for an internal package mirror, when the network
  requires one (`UV_INDEX_URL`, its older name, is deprecated);
- `UV_SYSTEM_CERTS=true` behind the corporate proxy (`corporate-proxy.md`);
- `UV_CACHE_DIR`, to move the cache to another drive.

## Disk

There is no `clean.ps1` here, deliberately. uv's cache lives outside the
project (`uv cache dir`) and is shared by every project on the machine, each
`.venv` on Windows holds hard links into it rather than copies (when both are
on the same drive), and PyInstaller rewrites `.build/` on each build. Nothing like Cargo's
`target/` grows per project.

When the disk is full anyway, in this order, stopping as soon as there is room:

1. `uv cache prune`: removes what no environment can use any more; costs nothing.
2. `.venv`, `dist/` and `.build/` in projects no longer worked on: `uv sync`
   and a build recreate them.
3. `uv cache clean`: the next sync downloads what it needs again.
4. Interpreters no longer pinned anywhere: `uv python list --only-installed`,
   then `uv python uninstall <version>`.
