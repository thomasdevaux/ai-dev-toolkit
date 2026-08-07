# SOURCE — session-report

`SKILL.md`, `analyze-sessions.mjs`, and `template.html` next to this file are
**third-party content**. Read them as someone else's work, not ours: don't
edit `analyze-sessions.mjs` or `template.html` in passing, and don't assume a
change here survives the next import.

- **upstream:** https://github.com/anthropics/claude-plugins-official
- **path:** `plugins/session-report/skills/session-report/`
- **commit:** `da7dc3b5ac4835a68584d6a9d53787fd5956ce8f` (2026-08-06)
- **license:** see `LICENSE`, which must travel with any copy
- **imported:** 2026-08-06

## What was imported, and what wasn't

Only the `session-report` skill directory. `analyze-sessions.mjs` and
`template.html` are imported byte-for-byte, unmodified.

## Local modifications

`SKILL.md` gained one sentence in the analyzer step and a closing note about
using `--since 1h` or `4h` for an end-of-session report, rather than the
7-day default. No code change was needed for this: `analyze-sessions.mjs`'s
`parseSince()` already accepts any `<N>h`/`<N>d` value generically — `1h`
and `4h` were never special cases to add, only use cases worth documenting
so the agent reaches for one after a single work session instead of always
reporting on the whole week.

The rest of `SKILL.md` is unmodified from upstream.

## Why this one

It's the closest built-in match to "help the end user learn from their own
token usage": it reads local transcripts directly (not the 24h billing
window `/usage` shows), and its own SKILL.md already asks the agent to
surface anomalies and optimization suggestions, not just raw numbers.

A `SessionEnd` hook used to advertise it on every session; it was removed
rather than made occasional, since the skill shows up in the session's skill
list on its own and a hook that speaks every time stops being read.

## Re-importing

Diff `analyze-sessions.mjs` and `template.html` against upstream at a newer
commit, re-apply the `SKILL.md` note about `4h` if upstream's own wording
changed, then update the pin and date here.
