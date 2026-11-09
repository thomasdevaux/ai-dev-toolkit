# Capability catalog

One row per capability the `gitlab-*` skills need. `subcommand` is what a
skill actually calls (see `invocation-path.md` for the exact invocation
form); `glab call` is what the subcommand does today; `MCP tool` is left as
`TBD` everywhere until an MCP GitLab server's tools are actually enumerated
at runtime (via `/mcp`) — **never fill this column from memory**. When an MCP
tool is confirmed, swapping a capability means changing that subcommand's
internal implementation only; no skill or caller changes, since every skill
only ever calls the subcommand name, never `glab` directly, for anything
listed here.

| Capability | Tier | Subcommand | `glab` call | MCP tool | Consumers |
|---|---|---|---|---|---|
| MR metadata | R | `mr get --iid N` | `GET projects/:id/merge_requests/N` | TBD — enumerate via `/mcp` | review, feedback |
| MR diff, filtered | R | `mr diff --iid N [--include P]` | `GET .../merge_requests/N/diffs` (paginated) | TBD | review, feedback |
| Per-file hunk map | R | `mr hunks --iid N --path P` | pure computation over `mr diff`'s diff text | n/a (local computation) | review, feedback |
| MR discussions | R | `mr discussions --iid N [--unresolved-only]` | `GET .../merge_requests/N/discussions` (paginated, system notes filtered) | TBD | feedback, review |
| MR's closed issue(s) | R | `mr closes-issues --iid N` | `GET .../merge_requests/N/closes_issues`, falls back to regexing the description for `Closes/Fixes/Resolves #N` | TBD | review |
| Issue (+ notes, + hierarchy) | R | `issue get --iid N [--with-hierarchy] [--comments]` | `GET .../issues/N` (+ `.../notes`), + a GraphQL work-item query when `--with-hierarchy` | TBD | plan, implement, review |
| Repo conventions (`CLAUDE.md`/`AGENTS.md`/duo instructions) | R | *(none — plain `Read`)* | n/a | n/a | all |
| General MR comment | W1 | `mr note create --iid N --kind K --body-file F [--expect-head-sha S] [--dry-run]` | `POST .../merge_requests/N/draft_notes` | TBD | review, feedback |
| Inline MR comment | W1 | `mr discussion create --iid N --kind K --path P --line L --side {old,new} --body-file F [--expect-head-sha S] [--dry-run]` | `POST .../merge_requests/N/draft_notes` with a validated `position`, or falls back to a general note | TBD | review |
| Reply to an MR thread | W1 | `mr discussion reply --iid N --kind K --discussion-id D --body-file F [--resolve] [--expect-head-sha S] [--dry-run]` | `POST .../merge_requests/N/draft_notes` with `in_reply_to_discussion_id` | TBD | feedback |
| Publish MR draft notes | W1 | `mr draft-notes publish --iid N [--dry-run]` | `POST .../merge_requests/N/draft_notes/bulk_publish` | TBD | review, feedback |
| Post/update an issue comment | W1 | `issue note create --iid N --kind K --body-file F [--dry-run]` / `issue note update --iid N --kind K --note-id ID --body-file F [--dry-run]` | `POST`/`PUT` `.../issues/N/notes[/ID]` (no draft-notes for issues — GitLab constraint) | TBD | plan |
| Find a marked issue comment | R | `issue note find-marker --iid N --marker STR` | `GET .../issues/N/notes` (paginated), scanned for the marker | TBD | plan, implement |
| Set an issue label | W1 | `issue label set --iid N --add LABEL [--dry-run]` | `PUT .../issues/N -F add_labels=...` | TBD | plan |
| Create a (Draft) MR | W2 | `mr create --title T --source B --target B --description-file F [--label L] [--closes-iid N] [--dry-run]` | `POST .../merge_requests` | TBD | implement |
| Branch / commit / push | — | *(none — plain `git`)* | n/a | n/a | feedback, implement |

## Out of tool scope (by design, not an oversight)

- `git` plumbing (fetch, worktree, switch, add, commit, push): local, no
  auth/transport help needed, and each skill's sequencing is already
  skill-specific logic a generic wrapper would not simplify.
- `glab mr view` / `glab issue view` used purely for human-readable display,
  where only one skill uses the call: not worth a wrapper.
- Repo-conventions reads: plain file reads, no GitLab round-trip, no parsing
  complex enough to be worth wrapping.
