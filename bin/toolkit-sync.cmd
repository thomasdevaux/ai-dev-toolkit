@echo off
rem Windows counterpart to ./toolkit-sync — see that file for why this cd
rem matters: `python -m tools.sync` needs its cwd inside the toolkit checkout.
rem %~dp0 is this script's own directory (bin\); the toolkit root is its parent.
rem Every subcommand also requires --toolkit-root, which is exactly the path
rem just resolved below — append it unless the caller already passed one.
for %%I in ("%~dp0..") do set "TOOLKIT_ROOT=%%~fI"
cd /d "%TOOLKIT_ROOT%"

if "%~1"=="" (
    python -m tools.sync %*
    goto :eof
)
echo %*| findstr /C:"--toolkit-root" >nul
if errorlevel 1 (
    python -m tools.sync %* --toolkit-root "%TOOLKIT_ROOT%"
) else (
    python -m tools.sync %*
)
