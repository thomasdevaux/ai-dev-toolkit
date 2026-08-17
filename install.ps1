# One-time per-machine bootstrap (PowerShell): clone (or update) ai-dev-toolkit
# into the same cache path /toolkit-sync reuses afterwards (so there's only
# ever one checkout on disk), then sync every user-scope baseline entry into
# ~/.claude/. See README.md for what that installs.
# Mirrors install.sh — keep both in sync.
$ErrorActionPreference = "Stop"

$Remote = if ($env:AI_DEV_TOOLKIT_REMOTE) { $env:AI_DEV_TOOLKIT_REMOTE } else { "https://github.com/thomasdevaux/ai-dev-toolkit.git" }
$CacheDir = if ($env:AI_DEV_TOOLKIT_ROOT) { $env:AI_DEV_TOOLKIT_ROOT } else { Join-Path $env:USERPROFILE ".cache\ai-dev-toolkit" }

if (Test-Path (Join-Path $CacheDir ".git")) {
    git -C $CacheDir pull --ff-only
} else {
    git clone $Remote $CacheDir
}
if ($LASTEXITCODE -ne 0) {
    # $ErrorActionPreference = "Stop" only turns cmdlet/script errors into
    # terminating ones — a failed native command like git still just returns,
    # and without this check the next line (Set-Location) fails instead with
    # a confusing "path not found" that hides the real git error above it.
    throw "git clone/pull failed (exit $LASTEXITCODE) — see the git output above"
}

Set-Location $CacheDir
python -m pip install --quiet -r tools\sync\requirements.txt
python -m tools.sync sync --user --toolkit-root . --yes-except-user-tools
