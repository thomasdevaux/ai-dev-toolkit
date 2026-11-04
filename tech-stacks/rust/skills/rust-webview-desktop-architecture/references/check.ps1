#Requires -Version 5.1
<#
The gate: the backend's and the front end's formatters, linters, type checker and tests, in
order, stopping at the first failure. Run it before landing a branch; CI runs the same file.
The same file in every project: copied from the toolkit's rust-webview-desktop-architecture
references, not forked. A project whose gate needs more (slow suites, e2e, a timing table)
writes its own check.ps1 under the same name, and keeps these steps in it.

  scripts/check.ps1

Steps:
  1. clean.ps1, the target/ cap;
  2. cargo fmt --check, clippy with warnings denied, cargo test, on the whole workspace;
  3. when the repository has a root package.json: its format:check, lint, typecheck and test
     scripts (they forward to the front-end package).

Windows PowerShell 5.1 compatible (no ternary, no `&&`).
#>

[CmdletBinding()]
param()

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
    & (Join-Path $PSScriptRoot 'clean.ps1')
    Invoke-Step 'cargo fmt' { cargo fmt --all -- --check }
    Invoke-Step 'cargo clippy' { cargo clippy --workspace --all-targets -- -D warnings }
    Invoke-Step 'cargo test' { cargo test --workspace }
    if (Test-Path (Join-Path $repoRoot 'package.json')) {
        Invoke-Step 'npm run format:check' { npm.cmd run format:check }
        Invoke-Step 'npm run lint' { npm.cmd run lint }
        Invoke-Step 'npm run typecheck' { npm.cmd run typecheck }
        Invoke-Step 'npm test' { npm.cmd test }
    }
    Write-Host 'All checks passed.' -ForegroundColor Green
}
finally {
    Pop-Location
}
