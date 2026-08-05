#!/bin/bash
# SessionStart hook: mechanical checks on AGENTS.md, and NOTHING when they all
# pass. A hook that speaks every session stops being read by the third one, so
# this only ever prints when there is something actually wrong. The judgment
# calls — density, routing, what's missing — belong to the audit-project-context
# skill, on demand.
set -u

project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
agents_md="$project_dir/AGENTS.md"
findings=""

add() { findings="${findings}${findings:+$'\n'}  - $1"; }

if [ ! -f "$agents_md" ]; then
  # Only worth mentioning where a context file is expected at all: a synced
  # project. Elsewhere, silence.
  if [ -f "$project_dir/.claude/.toolkit-sync-state" ]; then
    echo "context: no AGENTS.md in this project — run the init-project-context skill to create one."
  fi
  exit 0
fi

lines=$(wc -l < "$agents_md" | tr -d ' ')
if [ "$lines" -gt 200 ]; then
  add "AGENTS.md is $lines lines, over the 200-line cap — it loads on every session. Run audit-project-context."
elif [ "$lines" -gt 150 ]; then
  add "AGENTS.md is $lines lines, over the 150-line target — cut before adding."
fi

# Pointers to files that don't exist. Catches the doc that was renamed or the
# stub someone deleted, which is what silently turns the index into a maze.
while IFS= read -r path; do
  [ -z "$path" ] && continue
  [ -e "$project_dir/$path" ] || add "AGENTS.md points at '$path', which doesn't exist."
done <<EOF
$(grep -oE '(docs/[A-Za-z0-9._/-]+\.md|README\.md)' "$agents_md" | sort -u)
EOF

# Executable named first in each row of the Commands table: is it even
# installed? Deliberately shallow — it catches a documented toolchain nobody
# has, not a wrong flag. Restricted to table rows, so prose in the same
# section can't be mistaken for a command.
while IFS= read -r cmd; do
  [ -z "$cmd" ] && continue
  case "$cmd" in
    cd|ls|cat|echo|source|export|.) continue ;;
  esac
  command -v "$cmd" >/dev/null 2>&1 || add "AGENTS.md documents '$cmd', which isn't on PATH here."
done <<EOF
$(sed -n '/^## Commands/,/^## [^C]/p' "$agents_md" \
  | grep -E '^\|' \
  | grep -oE '^\| *`[a-zA-Z][a-zA-Z0-9._-]*' \
  | sed -E 's/^\| *`//' | sort -u)
EOF

if [ -n "$findings" ]; then
  echo "context check:"
  echo "$findings"
fi
exit 0
