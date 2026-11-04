#Requires -Version 5.1
<#
Keeps target/ (Rust's build cache) from filling the disk, and says how big it is.
The same file in every project: copied from the toolkit's rust-code-standards references,
not forked. A change goes into the toolkit first.

Why target/ grows: Cargo keeps every build it ever made, one per combination of dependency
version, feature set and profile, and never removes an old one. rustc also keeps one
incremental session per build and only drops the old ones when a build ends cleanly, so
interrupted builds leave full-size sessions behind. Nothing in it is precious: deleting it
costs one full rebuild, nothing else.

What it does, every time a launcher runs it:
  1. prunes the stale incremental sessions (the newest one of each crate stays): free;
  2. prints the size of the build dirs, so nobody discovers it from a full disk;
  3. past the cap, removes the build dirs entirely, as `cargo clean` would. The next build
     is then a full rebuild.

  scripts/clean.ps1             the three steps above, with the cap below
  scripts/clean.ps1 -MaxGB 60   another cap for this run
  scripts/clean.ps1 -Force      removes the build dirs now, whatever their size

The cap is 30 GB unless RUST_TARGET_MAX_GB says otherwise (one machine-wide setting for every
project; 0 = no cap). Build dirs are the cargo profile dirs (target/debug, target/release...);
what else sits in target/ (installers, logs, reports) is neither counted nor removed. A build
dir cargo is building in (its .cargo-lock is held) is left alone.

Windows PowerShell 5.1 compatible (no ternary, no `&&`).
#>

[CmdletBinding()]
param(
    [double]$MaxGB = -1,
    [switch]$Force,
    # The target dir; the repository's by default (the tests point it at a fake one).
    [string]$Target
)

$ErrorActionPreference = 'Stop'
$defaultMaxGB = 30
if ($MaxGB -lt 0) {
    if ($env:RUST_TARGET_MAX_GB) { $MaxGB = [double]$env:RUST_TARGET_MAX_GB } else { $MaxGB = $defaultMaxGB }
}
if (-not $Target) { $Target = Join-Path (Split-Path -Parent $PSScriptRoot) 'target' }
if (-not (Test-Path $Target)) { return }

$recursive = [System.IO.SearchOption]::AllDirectories
$recent = (Get-Date).AddMinutes(-10)

# Every cargo profile dir holds a `.fingerprint`.
$profileDirs = @(Get-ChildItem $Target -Directory -Recurse -Depth 3 -Force -Filter '.fingerprint' -ErrorAction SilentlyContinue |
        ForEach-Object { $_.Parent })

# Keeps the newest session of each crate, and anything touched in the last ten minutes (a
# build that is running now).
$pruned = 0
foreach ($profileDir in $profileDirs) {
    $root = Join-Path $profileDir.FullName 'incremental'
    if (-not (Test-Path $root)) { continue }
    foreach ($crate in Get-ChildItem $root -Directory) {
        $sessions = @(Get-ChildItem $crate.FullName -Directory | Sort-Object LastWriteTime -Descending)
        foreach ($old in ($sessions | Select-Object -Skip 1)) {
            if ($old.LastWriteTime -lt $recent) {
                Remove-Item -LiteralPath $old.FullName -Recurse -Force -ErrorAction SilentlyContinue
                $pruned++
            }
        }
    }
}
if ($pruned -gt 0) { Write-Host "pruned $pruned stale incremental sessions" -ForegroundColor DarkGray }

$size = 0L
foreach ($profileDir in $profileDirs) {
    foreach ($f in $profileDir.EnumerateFiles('*', $recursive)) { $size += $f.Length }
}
if ($MaxGB -gt 0) { $cap = 'removed past {0} GB' -f $MaxGB } else { $cap = 'no cap' }
Write-Host ('Rust build cache {0}: {1:N1} GB ({2}; scripts/clean.ps1 -Force frees it now)' -f $Target, ($size / 1GB), $cap) -ForegroundColor DarkGray
if (-not $Force -and ($MaxGB -le 0 -or $size -le $MaxGB * 1GB)) { return }

# Cargo holds .cargo-lock open for the whole build: deleting under it would break that build.
function Test-Building([System.IO.DirectoryInfo]$dir) {
    $lock = Join-Path $dir.FullName '.cargo-lock'
    if (-not (Test-Path $lock)) { return $false }
    try { ([System.IO.File]::Open($lock, 'Open', 'ReadWrite', 'None')).Dispose(); return $false }
    catch { return $true }
}

Write-Host ('removing the build dirs ({0:N1} GB): the next build is a full rebuild' -f ($size / 1GB)) -ForegroundColor Yellow
foreach ($profileDir in $profileDirs) {
    if (Test-Building $profileDir) {
        Write-Host "  kept $($profileDir.FullName): a build is running in it" -ForegroundColor DarkYellow
        continue
    }
    Remove-Item -LiteralPath $profileDir.FullName -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $profileDir.FullName) {
        # A running exe or an open pdb cannot be deleted: the rest is gone.
        Write-Host "  partly kept $($profileDir.FullName): files in use" -ForegroundColor DarkYellow
    }
}
