@echo off
rem Windows counterpart to ./toolkit-status — see toolkit-sync.cmd for why
rem %~dp0 is used instead of assuming cwd. Captures the caller's directory
rem in PROJECT_DIR before it's overridden by cd. The toolkit root is this
rem script's parent directory (bin\ sits one level below it).
set "PROJECT_DIR=%CD%"
if "%~1"=="--project-dir" set "PROJECT_DIR=%~2"
for %%I in ("%~dp0..") do set "TOOLKIT_ROOT=%%~fI"
cd /d "%TOOLKIT_ROOT%"

python -m tools.sync status --toolkit-root "%TOOLKIT_ROOT%" --project-dir "%PROJECT_DIR%"
echo.
echo (user scope: ~/.claude)
python -m tools.sync status --toolkit-root "%TOOLKIT_ROOT%" --project-dir "%PROJECT_DIR%" --user
