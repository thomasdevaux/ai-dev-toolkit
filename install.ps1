# One-time per-machine bootstrap (PowerShell): clone (or update) ai-dev-toolkit
# into the same cache path the session-start check reuses afterwards (so
# there's only ever one checkout on disk), then sync every user-scope
# baseline entry into ~/.claude/. See README.md for what that installs.
# Mirrors install.sh — keep both in sync.
$ErrorActionPreference = "Stop"

$Remote = if ($env:AI_DEV_TOOLKIT_REMOTE) { $env:AI_DEV_TOOLKIT_REMOTE } else { "https://github.com/thomasdevaux/ai-dev-toolkit.git" }
$CacheDir = if ($env:AI_DEV_TOOLKIT_ROOT) { $env:AI_DEV_TOOLKIT_ROOT } else { Join-Path $env:USERPROFILE ".cache\ai-dev-toolkit" }

if (Test-Path (Join-Path $CacheDir ".git")) {
    git -C $CacheDir pull --ff-only
} else {
    git clone $Remote $CacheDir
}

Set-Location $CacheDir
python -m tools.sync sync --user --toolkit-root .
