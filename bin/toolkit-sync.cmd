@echo off
rem Windows counterpart to ./toolkit-sync — see that file for why this cd
rem matters: `python -m tools.sync` needs its cwd inside the toolkit checkout.
rem %~dp0 is this script's own directory (bin\); the toolkit root is its parent.
for %%I in ("%~dp0..") do set "TOOLKIT_ROOT=%%~fI"
cd /d "%TOOLKIT_ROOT%"
python -m tools.sync %*
