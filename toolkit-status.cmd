@echo off
rem Windows counterpart to ./toolkit-status — see toolkit-sync.cmd for why
rem %~dp0 is used instead of assuming cwd. Captures the caller's directory
rem in PROJECT_DIR before it's overridden by cd. %~dp0 ends in a trailing
rem backslash, which escapes a closing quote if used as "%~dp0" directly —
rem strip it before quoting.
set "PROJECT_DIR=%CD%"
if "%~1"=="--project-dir" set "PROJECT_DIR=%~2"
set "TOOLKIT_ROOT=%~dp0"
set "TOOLKIT_ROOT=%TOOLKIT_ROOT:~0,-1%"
cd /d "%TOOLKIT_ROOT%"

python -m tools.sync status --toolkit-root "%TOOLKIT_ROOT%" --project-dir "%PROJECT_DIR%"
echo.
echo (user scope: ~/.claude)
python -m tools.sync status --toolkit-root "%TOOLKIT_ROOT%" --project-dir "%PROJECT_DIR%" --user
