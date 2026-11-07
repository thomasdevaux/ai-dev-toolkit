# Front-end feedback on Tauri

What differs from the procedure in `SKILL.md`.

- **Front-end package:** the one holding `main.tsx`.
- **Debugging port and launcher:** the launcher runs `tauri dev` with
  `$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9222 --remote-allow-origins=*'`,
  and clears it afterwards. Nothing is compiled in, so a release build has no
  port unless that variable is set on the machine running it.
- **First start:** the first debug build is slow.
- **Window check fails:** the variable did not reach WebView2. Check that the
  launcher sets it in the process that runs `tauri dev`.
- **Fix loop:** Rust edits rebuild and restart the app.
