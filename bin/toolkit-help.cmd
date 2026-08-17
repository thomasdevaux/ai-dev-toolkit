@echo off
rem Windows counterpart to ./toolkit-help — see toolkit-sync.cmd for why
rem %~dp0 is used instead of assuming cwd. The toolkit root is this script's
rem parent directory (bin\ sits one level below it).
echo https://github.com/thomasdevaux/ai-dev-toolkit/tree/main/handbook
echo.
for %%I in ("%~dp0..") do set "TOOLKIT_ROOT=%%~fI"
type "%TOOLKIT_ROOT%\handbook\practices.md"
