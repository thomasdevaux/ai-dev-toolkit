# Toolkit sync: never run it yourself

Never run `python -m tools.sync sync` (Bash) to apply a sync — however it
came up: `/toolkit-sync`, or the user just typing "sync the toolkit".

Give the user the exact command instead, and let them run it themselves
(the `!` prefix, or their own terminal). `/toolkit-sync` already does this
when it finds drift or pending onboarding — reuse its command rather than
composing a new one.

**Why:** the filesystem mutation stays a deliberate action the user takes
and reviews, not something an agent applies on their behalf.
