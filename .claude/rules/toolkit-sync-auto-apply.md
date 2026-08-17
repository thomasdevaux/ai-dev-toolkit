# Toolkit sync: the agent applies it directly

`/toolkit-sync` and `/toolkit-feat` run `bin/toolkit-sync` themselves — sync,
switch, and dismiss alike — instead of printing the command for the user to
paste after a `!`. This applies however the request came up: the slash
commands, or the user just typing "sync the toolkit".

Always pass `--yes`, never `--yes-except-user-tools` — the latter still
blocks on an interactive `[y/N]` prompt for entries sourced from
`user-tools/` (e.g. the statusline), and a `Bash` tool call has no stdin to
answer it with; it would hang, not degrade gracefully.

After applying, report what changed: the feature summary `sync_entries`
prints (`Syncing: + ...`), or `dismiss`'s one-line confirmation. That
report is what keeps this reviewable — the user sees the outcome even
though they didn't gate it.

**Why:** overwriting a toolkit-managed file that the user hand-edited
outside of sync is an accepted risk, not something this rule protects
against — sync only ever prunes files it tracked writing itself
(`state.files`), so a hand-added file or hand-installed plugin was never a
deletion candidate either way. With that risk assumed, requiring a
copy-paste through `!` added a step most users would run unread anyway,
without adding real protection.
