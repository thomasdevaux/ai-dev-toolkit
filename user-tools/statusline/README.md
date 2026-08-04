# statusline

A single-line, color-coded Claude Code status line: model/effort/thinking
flags, a context-window progress bar, and 5h/7d rate-limit usage with time
to reset.

## Install

```
python -m tools.sync sync user-statusline --toolkit-root . --user
```

This copies `statusline.py` to `~/.claude/statusline.py` and merges a
`statusLine` entry into `~/.claude/settings.json` (only that key — every
other setting is left untouched). Confirm the diff when prompted.

## Uninstall

1. Remove the `statusLine` key from `~/.claude/settings.json` (or point it
   at a different command).
2. Delete `~/.claude/statusline.py`.
3. Remove the `user-statusline` entry from `~/.claude/.toolkit-sync-state`
   if you're also dropping the toolkit's user-scope sync entirely.

There's no automated uninstall command — `tools/sync` only ever adds or
updates files and settings, never removes them, by design.

## How it reads

`statusLine.type: "command"` runs `python ~/.claude/statusline.py` on
every prompt, piping the status-line JSON payload (model, context window,
rate limits — see Claude Code's status line docs for the schema) to its
stdin. Every optional field is handled gracefully: a field missing from a
given session's input (effort, thinking, fast_mode, rate_limits, ...) is
simply dropped from the line rather than shown as blank or broken.
