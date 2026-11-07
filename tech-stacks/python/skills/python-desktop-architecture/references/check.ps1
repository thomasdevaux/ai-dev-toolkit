#Requires -Version 5.1
<#
The gate: the environment, the formatter, the linter, the type checker and the tests, in order,
stopping at the first failure. The merge runs it (git-workflow-app), or CI does.
The same file in every project: copied from the toolkit's python-desktop-architecture
references, not forked. A project whose gate needs more (slow suites, a clean-machine build
test) writes its own check.ps1 under the same name, and keeps these steps in it.

  scripts/check.ps1          the `full` command
  scripts/check.ps1 -Fast    the `fast` command: the same checks, minus pytest

Steps:
  1. uv sync --locked: the environment matches uv.lock, and uv.lock matches pyproject.toml;
  2. ruff format --check, ruff check, mypy on the source trees, pytest;
  3. the interface boundary: nothing the GUI-free code imports, directly or not, is an interface
     framework. GUI-free means src/<name>/core and src/<name>/cli when they exist, and every
     package under packages/. Nothing in Python enforces this, so the gate does. Each module is
     imported, so it must have no side effect at import time - a rule worth holding anyway.

Windows PowerShell 5.1 compatible (no ternary, no `&&`).
#>

[CmdletBinding()]
param([switch]$Fast)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Step {
    param([string]$Name, [scriptblock]$Command)
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Name" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# Imports every module of the packages named on the command line, and fails if an interface
# framework ends up loaded: transitive leaks included, which a text search would miss.
# The AST pass also catches an import placed inside a function, which importing does not run.
$boundaryCheck = @'
import ast, importlib, importlib.util, sys
from pathlib import Path
FORBIDDEN = {"PySide6", "PyQt6", "PyQt5", "PySide2", "tkinter"}

def loaded():
    return {name.split(".")[0] for name in sys.modules} & FORBIDDEN

def direct(path):
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), str(path))):
        if isinstance(node, ast.Import):
            found |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found & FORBIDDEN

def modules(root):
    # Listed from the disk rather than walked, which would import packages unobserved.
    base = Path(importlib.util.find_spec(root).submodule_search_locations[0])
    for path in sorted(base.rglob("*.py")):
        parts = path.relative_to(base).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        yield ".".join((root,) + parts), path

leaks = set()
for root in sys.argv[1:]:
    before = loaded()
    found = list(modules(root))  # finding demoapp.core runs demoapp/__init__.py
    leaks |= {f"{root}'s parent package loads {f}" for f in loaded() - before}
    for name, path in found:
        before = loaded()
        importlib.import_module(name)
        # The first module to pull a framework in gets the blame, its parent packages'
        # __init__ included; the others are listed once it is fixed.
        leaks |= {f"{name} loads {f}" for f in loaded() - before}
        leaks |= {f"{name} imports {f}" for f in direct(path)}
for leak in sorted(leaks):
    print("  " + leak)
sys.exit(1 if leaks else 0)
'@

Push-Location $repoRoot
try {
    Invoke-Step 'uv sync --locked' { uv sync --locked --all-packages }

    $sources = @()
    foreach ($tree in @('src', 'packages/*/src', 'apps/*/src')) {
        $sources += @(Resolve-Path -Path $tree -Relative -ErrorAction SilentlyContinue)
    }

    Invoke-Step 'ruff format' { uv run --no-sync ruff format --check }
    Invoke-Step 'ruff check' { uv run --no-sync ruff check }
    Invoke-Step 'mypy' { uv run --no-sync mypy @sources }
    if (-not $Fast) {
        Write-Host '==> pytest' -ForegroundColor Cyan
        uv run --no-sync pytest
        # 5 = no test collected: a new project, not a failure.
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 5) {
            Write-Host 'FAILED: pytest' -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }

    $roots = @()
    foreach ($dir in @(Get-ChildItem -Path 'src/*/core', 'src/*/cli' -Directory -ErrorAction SilentlyContinue)) {
        $roots += "$($dir.Parent.Name).$($dir.Name)"
    }
    foreach ($dir in @(Get-ChildItem -Path 'packages/*/src/*' -Directory -ErrorAction SilentlyContinue)) {
        if (Test-Path (Join-Path $dir.FullName '__init__.py')) { $roots += $dir.Name }
    }
    if ($roots.Count -gt 0) {
        Write-Host "==> no interface framework in $($roots -join ', ')" -ForegroundColor Cyan
        $boundaryCheck | uv run --no-sync python - @roots
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'FAILED: GUI-free code reaches an interface framework (above)' -ForegroundColor Red
            exit 1
        }
    }
    Write-Host 'All checks passed.' -ForegroundColor Green
}
finally {
    Pop-Location
}
