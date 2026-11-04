#Requires -Version 5.1
# Tests of clean.ps1 on a fake target dir. Exits 1 on the first failure.
# The same file in every project of the portfolio, like clean.ps1.

$ErrorActionPreference = 'Stop'
$clean = Join-Path $PSScriptRoot 'clean.ps1'
$target = Join-Path ([System.IO.Path]::GetTempPath()) ("rust-clean-test-" + [guid]::NewGuid())
$savedCap = $env:RUST_TARGET_MAX_GB

function New-File([string]$path, [int]$bytes, [datetime]$written = (Get-Date)) {
    New-Item -ItemType Directory -Force (Split-Path -Parent $path) | Out-Null
    [System.IO.File]::WriteAllBytes($path, [byte[]]::new($bytes))
    (Get-Item $path).LastWriteTime = $written
}

function New-FakeTarget {
    if (Test-Path $target) { Remove-Item -LiteralPath $target -Recurse -Force }
    $old = (Get-Date).AddHours(-1)
    New-File "$target/debug/.fingerprint/a-0123456789abcdef/lib-a" 16
    New-File "$target/debug/deps/liba-0123456789abcdef.rlib" 1MB
    New-File "$target/xcp-eth/debug/.fingerprint/b-fedcba9876543210/lib-b" 16
    New-File "$target/xcp-eth/debug/deps/libb-fedcba9876543210.rlib" 1MB
    New-File "$target/debug/incremental/a-2xlg3ywvsetej/s-old/x.bin" 1KB $old
    (Get-Item "$target/debug/incremental/a-2xlg3ywvsetej/s-old").LastWriteTime = $old
    New-File "$target/debug/incremental/a-2xlg3ywvsetej/s-new/x.bin" 1KB
    New-File "$target/package/app.msi" 1MB
    New-File "$target/gate-full.log" 1KB
}

function Assert([bool]$condition, [string]$what) {
    if (-not $condition) {
        Write-Host "FAILED: $what" -ForegroundColor Red
        Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue
        $env:RUST_TARGET_MAX_GB = $savedCap
        exit 1
    }
}

try {
    $env:RUST_TARGET_MAX_GB = $null
    New-FakeTarget
    $out = (& $clean -Target $target 6>&1) -join "`n"
    Assert (Test-Path "$target/debug/deps/liba-0123456789abcdef.rlib") 'under the default cap, the build dirs stay'
    Assert (-not (Test-Path "$target/debug/incremental/a-2xlg3ywvsetej/s-old")) 'an old incremental session goes'
    Assert (Test-Path "$target/debug/incremental/a-2xlg3ywvsetej/s-new") 'the newest incremental session stays'
    Assert ($out -match 'Rust build cache .*: 0[.,]0 GB \(removed past 30 GB') 'the size and the default cap are printed'

    $env:RUST_TARGET_MAX_GB = '0'
    $out = (& $clean -Target $target 6>&1) -join "`n"
    Assert (Test-Path "$target/debug/deps/liba-0123456789abcdef.rlib") 'with the cap disabled, the build dirs stay'
    Assert ($out -match 'no cap') 'a disabled cap is printed as such'

    $env:RUST_TARGET_MAX_GB = '0.001'
    & $clean -Target $target 6>$null
    Assert (-not (Test-Path "$target/debug")) 'over the cap from the environment, target/debug goes'
    Assert (-not (Test-Path "$target/xcp-eth/debug")) 'over the cap, a nested build dir goes'
    Assert (Test-Path "$target/package/app.msi") 'what is not a build dir stays'
    Assert (Test-Path "$target/gate-full.log") 'files at the root of target stay'

    $env:RUST_TARGET_MAX_GB = $null
    New-FakeTarget
    & $clean -Target $target -MaxGB 0.001 6>$null
    Assert (-not (Test-Path "$target/debug")) '-MaxGB overrides the default cap'

    New-FakeTarget
    $lock = [System.IO.File]::Open("$target/debug/.cargo-lock", 'Create', 'ReadWrite', 'None')
    try { & $clean -Target $target -Force 6>$null } finally { $lock.Dispose() }
    Assert (Test-Path "$target/debug/deps/liba-0123456789abcdef.rlib") 'a build dir being built in stays'
    Assert (-not (Test-Path "$target/xcp-eth/debug")) 'the others go'

    Write-Host 'clean.ps1: all tests passed'
}
finally {
    $env:RUST_TARGET_MAX_GB = $savedCap
    Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue
}
