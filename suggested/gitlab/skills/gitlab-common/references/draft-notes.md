# Publishing through draft notes

Used by every skill that writes comments on an MR. Read `conventions.md` first.

Everything posted (general comments, inline notes, replies, thread
resolutions) is created as **draft notes**, shown to the user, then published
together in one `mr draft-notes publish` call. A direct `notes`/`discussions`
POST notifies the author immediately per comment; draft notes send a single
notification for the whole batch and stay editable/removable in the GitLab UI
until published. Do not fall back to direct posting: if a draft-note call
fails, report the failure.

## Procedure

1. **Show the exact list once, with the question.** For each candidate, run
   the relevant write subcommand with `--dry-run` and show its `payload` (the
   exact text and, for inline notes, the resolved `position`) plus whether
   `duplicate_found` came back true — that output *is* the preview; do not
   hand-format a separate one. State what was left out and why. Then ask what
   to post, in that same message: none / general only / everything / a subset.
   **That answer is the confirmation** — one round trip, not two. Do not show
   the list, collect a choice, then reprint it and ask "confirm?" again;
   and if the exact texts were already shown earlier in this conversation (the
   report of `gitlab-mr-review` step 5, the reply table of `gitlab-mr-feedback`
   step 5), do not reprint them — refer to the candidate numbers. Re-ask only
   if something changed since the user saw them (the MR head moved, a text
   was edited, a duplicate appeared). A bare "yes" to a vague proposal is not
   consent; a choice made against texts the user has seen is.
2. **Freshness**: pass `--expect-head-sha $(git rev-parse HEAD)` (the
   worktree's/branch's current head) to every write call that anchors to the
   diff (`mr note create`, `mr discussion create`). The tool re-fetches the
   MR fresh and aborts with a stale-state error if it has moved since — say
   so and ask whether to re-fetch and redo before posting anything anchored to
   a stale diff. `mr discussion reply` and `mr draft-notes publish` are not
   diff-anchored and don't need this flag.
3. **Create only what was confirmed**, dropping `--dry-run`:
   - General note: `mr note create --iid <iid> --kind <kind> --body-file <file> --expect-head-sha <sha>`.
   - Inline note: `mr discussion create --iid <iid> --kind <kind> --path <path> --line <line> --side {old,new} --body-file <file> --expect-head-sha <sha>`.
     The tool computes and validates the `position` itself from the current
     diff's hunks (added → `new_line` only; removed → `old_line` only;
     unchanged context line → both). If the requested line is outside every
     hunk, it automatically falls back to a general comment and reports why
     (`fell_back_general`, `fallback_reason`) — it never guesses a nearby
     line. Say so in the report when that happens.
   - Reply to an existing thread: `mr discussion reply --iid <iid> --kind <kind> --discussion-id <id> --body-file <file> [--resolve]` —
     `--resolve` only when the skill's rules allow resolving that thread.
   - A call that returns `"status": "skipped_duplicate"` means the exact same
     content was already posted (by hash, not by exact bytes — trivial
     rewrapping doesn't defeat this) — report it as already-done, not as an
     error.
4. **Publish once**: `mr draft-notes publish --iid <iid>`. If any individual
   draft failed to create, stop and ask before publishing the rest — a partial
   batch may not match what the user confirmed.
5. Report exactly what was published (with resulting note/discussion ids) and
   what was skipped (including anything skipped as a duplicate).
