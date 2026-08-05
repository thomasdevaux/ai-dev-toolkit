---
paths:
  - "pyproject.toml"
  - "setup.py"
  - "setup.cfg"
---

# Python packaging

- Use `pyproject.toml` with a `[build-system]` section (`setuptools` or
  `hatchling`) for any tool meant to be installed, not a bare `setup.py`.
- Pin direct dependencies with a compatible-release range (`~=`), not an
  exact pin, unless a known incompatibility requires it.
- Declare a `[project.scripts]` entry point for any tool with a CLI, instead
  of telling users to run `python path/to/script.py`.
- Set `requires-python` to the actual minimum version the code is tested
  against.
- Do not commit a `dist/` or `build/` directory; add them to `.gitignore`.
- After changing dependencies: if the project uses `uv` or `Poetry`, its
  lock file (`uv.lock` / `poetry.lock`) is regenerated automatically by
  `uv add`/`uv sync` or `poetry add`/`poetry lock` — just commit the
  updated lock file, don't hand-edit it. If the project uses plain `pip`
  with no native lock mechanism, use `pip-tools` (or `uv pip compile`)
  to regenerate a pinned requirements file after every dependency change.
  Avoid `pip freeze > requirements.txt` — it captures the entire
  environment including development tooling and pins transitive
  dependencies with no provenance.
