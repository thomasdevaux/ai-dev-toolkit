# SOURCE — caveman

`SKILL.md` next to this file is **third-party content, copied verbatim**. Read
it as someone else's work, not ours: don't edit it in passing, and don't
assume a change here survives the next import.

- **upstream:** https://github.com/JuliusBrussee/caveman
- **commit:** `ec83e5bace4c20484d704dea21e12fc4eb94e9aa` (2026-08-04)
- **license:** MIT — see `LICENSE`, which must travel with any copy
- **imported:** 2026-08-05
- **local modifications:** none

## What was imported, and what wasn't

Only `skills/caveman/SKILL.md`. Upstream also ships a `cavecrew` agent trio,
`caveman-commit` / `caveman-review` / `caveman-stats` commands, a
`caveman-compress` skill with Python scripts, a Node CLI installer and a
plugin marketplace manifest. None of it is here: that's a separate set of
decisions about how a team works, and adopting it wholesale would smuggle in
choices nobody made.

Its `README.md` was dropped — a README inside a synced `.claude/skills/`
directory is noise in the consumer's repo.

**We use neither the upstream `install.sh`, nor the npm package, nor the
plugin marketplace.** Copying the text is the point: it's readable, diffable,
versioned here, and a consuming project gets an ordinary file it owns.

## Why this one

It preserves what compression must never touch — the user's language, code
blocks, API names, exact error strings — and it steps aside on its own for
security warnings and irreversible actions. Those properties are what make it
safe to ship in the baseline; **re-verify them before bumping the pin.**

Its README claims ~65% fewer output tokens on prose and ~8.5% on agentic
coding runs. Those are the author's numbers, on the author's benchmarks — see
`handbook/token-economy.md` for what we measured.

## Re-importing

Diff `SKILL.md` against upstream at a newer commit, re-read the safety
properties above, then update the pin and date here.
