<#
Dot-sourced by the scripts that reach the npm registry (directly or through wails3 or tauri). On a machine
behind a TLS-inspecting proxy, Node does not trust the corporate root CA, which npm reports as
UNABLE_TO_GET_ISSUER_CERT_LOCALLY. `--use-system-ca` makes Node trust the OS certificate store
(the one browsers already use), with TLS verification left on.

Only adds the flag when this Node supports it (22.15+, or 23.8+) and the caller has not already
set it; any other NODE_OPTIONS the caller defined is kept.
#>
function Enable-NodeSystemCa {
    $raw = (& node --version 2>$null)
    if (-not $raw -or $raw -notmatch '^v(\d+)\.(\d+)') { return }
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    $supported = ($major -ge 24) -or ($major -eq 23 -and $minor -ge 8) -or ($major -eq 22 -and $minor -ge 15)
    if (-not $supported) { return }
    if ($env:NODE_OPTIONS -match '--use-system-ca') { return }
    $env:NODE_OPTIONS = ("$env:NODE_OPTIONS --use-system-ca").Trim()
}

Enable-NodeSystemCa
