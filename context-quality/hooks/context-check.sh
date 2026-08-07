#!/bin/bash
# SessionStart hook: mechanical checks on AGENTS.md, and NOTHING when they all
# pass. A hook that speaks every session stops being read by the third one, so
# this only ever prints when there is something actually wrong. The judgment
# calls — density, routing, what's missing — belong to the audit-project-context
# skill, on demand.
set -u

# Commits allowed to land without AGENTS.md moving before the staleness nudge
# fires. Tunable: low enough that the nudge actually happens on a normal repo,
# high enough that it is not a session-start fixture.
STALE_COMMITS=40

project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
agents_md="$project_dir/AGENTS.md"
state_file="$project_dir/.claude/.context-check-state"
findings=""

add() { findings="${findings}${findings:+$'\n'}  - $1"; }

if [ ! -f "$agents_md" ]; then
  # Only worth mentioning where a context file is expected at all: a synced
  # project that has not adopted project-type-none. That profile states
  # outright that no document set is imposed, so nagging it for an AGENTS.md
  # would contradict a rule the same toolkit ships.
  if [ -f "$project_dir/.claude/.toolkit-sync-state" ] \
     && [ ! -f "$project_dir/.claude/rules/no-project-type.md" ]; then
    echo "context: no AGENTS.md in this project — type /init-project-context to create one."
  fi
  exit 0
fi

# grep -c '' counts lines, not newlines: a file without a trailing newline is
# not undercounted by one the way wc -l does it.
lines=$(grep -c '' "$agents_md")
if [ "$lines" -gt 200 ]; then
  add "AGENTS.md is $lines lines, over the 200-line cap — it loads on every session. Run /audit-project-context."
elif [ "$lines" -gt 150 ]; then
  add "AGENTS.md is $lines lines, over the 150-line target — cut before adding."
fi

# Pointers to files that don't exist. Catches the doc that was renamed or the
# stub someone deleted, which is what silently turns the index into a maze.
#
# Markdown link targets only, and fenced code blocks stripped first. A bare
# path in prose is not a pointer — the rule's own text ("never invent
# docs/notes.md") would otherwise be reported as a dead link by any project
# that quotes it. The cost of that precision is that a pointer written as bare
# text goes unchecked; the skeleton uses links, so write them as links.
while IFS= read -r path; do
  [ -z "$path" ] && continue
  case "$path" in
    http://*|https://*|mailto:*|\#*) continue ;;
  esac
  # Drop any #anchor before testing the path on disk.
  [ -e "$project_dir/${path%%#*}" ] || add "AGENTS.md points at '$path', which doesn't exist."
done <<EOF
$(awk '/^[[:space:]]*```/ { fenced = !fenced; next } !fenced' "$agents_md" \
  | grep -oE '\]\([^)]+\)' \
  | sed -E 's/^\]\(|\)$//g' | sort -u)
EOF

# Executable named first in each row of the Commands table: is it even
# installed? Deliberately shallow — it catches a documented toolchain nobody
# has, not a wrong flag. Restricted to table rows inside that one section, so
# prose and later sections can't be mistaken for commands.
while IFS= read -r cmd; do
  [ -z "$cmd" ] && continue
  case "$cmd" in
    cd|ls|cat|echo|source|export|.) continue ;;
  esac
  command -v "$cmd" >/dev/null 2>&1 || add "AGENTS.md documents '$cmd', which isn't on PATH here."
done <<EOF
$(sed -n '/^## Commands/,/^## /{ /^## /d; p; }' "$agents_md" \
  | grep -E '^\|' \
  | grep -oE '^\| *`[a-zA-Z][a-zA-Z0-9._-]*' \
  | sed -E 's/^\| *`//' | sort -u)
EOF

# Staleness. Size and dead paths are the cheap checks; what actually rots is
# accuracy — an invariant that stopped being true, a command whose behaviour
# changed — and no mechanical test catches that. What is measurable is the
# proxy: the repository moved a long way and the context file didn't. The
# nudge points at the skill that does the real work.
if git -C "$project_dir" rev-parse --git-dir >/dev/null 2>&1; then
  last_touch=$(git -C "$project_dir" log -1 --format=%H -- AGENTS.md 2>/dev/null)
  if [ -n "$last_touch" ]; then
    since=$(git -C "$project_dir" rev-list --count "$last_touch"..HEAD 2>/dev/null || echo 0)
    nudged_at=0
    [ -f "$state_file" ] && nudged_at=$(cat "$state_file" 2>/dev/null || echo 0)
    case "$nudged_at" in *[!0-9]*|"") nudged_at=0 ;; esac
    # AGENTS.md moved since the last nudge: forget that we ever nudged.
    [ "$since" -lt "$nudged_at" ] && nudged_at=0

    if [ "$since" -ge "$STALE_COMMITS" ] && [ "$since" -ge $((nudged_at + STALE_COMMITS)) ]; then
      add "AGENTS.md hasn't changed in $since commits — run /audit-project-context to check it's still accurate."
      mkdir -p "$(dirname "$state_file")" && echo "$since" > "$state_file"
    fi
  fi
fi

if [ -n "$findings" ]; then
  echo "context check:"
  echo "$findings"
fi
exit 0
