#Requires -Version 5.1
<#
The gate: the backend's and the front end's formatters, linters, type checker and tests, in
order, stopping at the first failure. The merge runs it (git-workflow-app), or CI does.
The same file in every project: copied from the toolkit's go-webview-desktop-architecture
references, not forked. A project whose gate needs more (slow suites, e2e, a timing table)
writes its own check.ps1 under the same name, and keeps these steps in it.

  scripts/check.ps1          the `full` command
  scripts/check.ps1 -Fast    the `fast` command: the same checks, minus go test, the bindings
                             regeneration and the front end's tests

Steps:
  1. frontend/dist exists: main.go embeds it and it is gitignored, so on a fresh clone every Go
     step would otherwise fail on the //go:embed pattern. A placeholder is enough, and the next
     real front-end build replaces it;
  2. golangci-lint fmt --diff, golangci-lint run, go test, on the whole module;
  3. when internal/domain exists: nothing it imports, directly or not, is Wails. The compiler
     does not guarantee this in a single module, so the gate does;
  4. when frontend/package.json exists: bindings regenerated from the Go services, then the
     front end's format:check, lint, typecheck and test scripts.

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
    $dist = Join-Path $repoRoot 'frontend/dist'
    if (-not (Test-Path $dist)) {
        New-Item -ItemType Directory -Path $dist | Out-Null
        New-Item -ItemType File -Path (Join-Path $dist '.gitkeep') | Out-Null
    }

    Invoke-Step 'golangci-lint fmt' { golangci-lint fmt --diff }
    Invoke-Step 'golangci-lint run' { golangci-lint run }
    if (-not $Fast) { Invoke-Step 'go test' { go test ./... } }

    if (Test-Path (Join-Path $repoRoot 'internal/domain')) {
        Write-Host '==> internal/domain is free of Wails' -ForegroundColor Cyan
        $deps = @(go list -deps ./internal/domain/...)
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'FAILED: go list on internal/domain' -ForegroundColor Red
            exit $LASTEXITCODE
        }
        $leaks = @($deps | Where-Object { $_ -like 'github.com/wailsapp/wails*' })
        if ($leaks.Count -gt 0) {
            Write-Host 'FAILED: internal/domain depends on Wails through:' -ForegroundColor Red
            $leaks | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
            exit 1
        }
    }

    if (Test-Path (Join-Path $repoRoot 'frontend/package.json')) {
        if (-not $Fast) { Invoke-Step 'wails3 generate bindings' { wails3 task common:generate:bindings } }
        Invoke-Step 'npm run format:check' { npm.cmd --prefix frontend run format:check }
        Invoke-Step 'npm run lint' { npm.cmd --prefix frontend run lint }
        Invoke-Step 'npm run typecheck' { npm.cmd --prefix frontend run typecheck }
        if (-not $Fast) { Invoke-Step 'npm test' { npm.cmd --prefix frontend test } }
    }
    Write-Host 'All checks passed.' -ForegroundColor Green
}
finally {
    Pop-Location
}
