@echo off
rem Windows counterpart to ./toolkit-sync — see that file for why this cd
rem matters: `python -m tools.sync` needs its cwd inside the toolkit checkout.
cd /d "%~dp0"
python -m tools.sync %*
