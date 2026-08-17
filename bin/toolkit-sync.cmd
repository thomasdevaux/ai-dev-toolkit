@echo off
rem Windows counterpart to ./toolkit-sync — see that file for why this cd
rem matters: `python -m tools.sync` needs its cwd inside the toolkit checkout.
rem %~dp0 is this script's own directory (bin\); the toolkit root is its parent.
rem CALLER_DIR is captured before that cd: --project-dir defaults to Python's
rem own cwd when omitted, which would otherwise silently become the toolkit
rem root once we've cd'd there instead of wherever the caller ran this from.
set "CALLER_DIR=%CD%"
for %%I in ("%~dp0..") do set "TOOLKIT_ROOT=%%~fI"
cd /d "%TOOLKIT_ROOT%"

if "%~1"=="" (
    python -m tools.sync %*
    goto :eof
)

set "HAS_ROOT="
echo %*| findstr /C:"--toolkit-root" >nul
if not errorlevel 1 set "HAS_ROOT=1"

set "HAS_PROJECT="
echo %*| findstr /C:"--project-dir" >nul
if not errorlevel 1 set "HAS_PROJECT=1"

if defined HAS_ROOT (
    if defined HAS_PROJECT (
        python -m tools.sync %*
    ) else (
        python -m tools.sync %* --project-dir "%CALLER_DIR%"
    )
) else (
    if defined HAS_PROJECT (
        python -m tools.sync %* --toolkit-root "%TOOLKIT_ROOT%"
    ) else (
        python -m tools.sync %* --toolkit-root "%TOOLKIT_ROOT%" --project-dir "%CALLER_DIR%"
    )
)
