# Toolkit sync: never run it yourself

Never run `python -m tools.sync sync` (Bash) to apply a sync — however it
came up: session-start drift, `/toolkit-sync`, or the user just typing
"sync the toolkit".

Confirm with `AskUserQuestion` instead, offering exactly these three options,
labelled verbatim: `Sync now`, `Show details first`, `Not now`. Word the
question itself however you like, in the user's language — a `PostToolUse`
hook matches the option set, not the wording, and applies the sync itself.
It reports back whether it succeeded.

**Why:** the filesystem mutation stays script-driven automation rather than
an agent-issued Bash call.
