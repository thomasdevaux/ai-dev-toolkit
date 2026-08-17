@echo off
rem Windows counterpart to ./toolkit-help — see toolkit-sync.cmd for why
rem %~dp0 is used instead of assuming cwd.
echo https://github.com/thomasdevaux/ai-dev-toolkit/tree/main/handbook
echo.
type "%~dp0handbook\practices.md"
