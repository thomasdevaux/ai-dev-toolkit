#Requires -Version 5.1
<#
The gate: the backend's and the front end's formatters, linters, type checker and tests, in
order, stopping at the first failure. The merge runs it (git-workflow-app), or CI does.
The same file in every project: copied from the toolkit's rust-webview-desktop-architecture
references, not forked. A project whose gate needs more (slow suites, e2e, a timing table)
writes its own check.ps1 under the same name, and keeps these steps in it.

  scripts/check.ps1          the `full` command
  scripts/check.ps1 -Fast    the `fast` command: the same checks, minus clean.ps1 and the tests

Steps:
  1. clean.ps1, the target/ cap;
  2. cargo fmt --check, clippy with warnings denied, cargo test, on the whole workspace;
  3. when the repository has a root package.json: its format:check, lint, typecheck and test
     scripts (they forward to the front-end package).

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

Push-Location $repoRoot
try {
    if (-not $Fast) { & (Join-Path $PSScriptRoot 'clean.ps1') }
    Invoke-Step 'cargo fmt' { cargo fmt --all -- --check }
    Invoke-Step 'cargo clippy' { cargo clippy --workspace --all-targets -- -D warnings }
    if (-not $Fast) { Invoke-Step 'cargo test' { cargo test --workspace } }
    if (Test-Path (Join-Path $repoRoot 'package.json')) {
        Invoke-Step 'npm run format:check' { npm.cmd run format:check }
        Invoke-Step 'npm run lint' { npm.cmd run lint }
        Invoke-Step 'npm run typecheck' { npm.cmd run typecheck }
        if (-not $Fast) { Invoke-Step 'npm test' { npm.cmd test } }
    }
    Write-Host 'All checks passed.' -ForegroundColor Green
}
finally {
    Pop-Location
}
