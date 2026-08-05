#!/bin/bash
# SessionStart hook: says something ONLY when the CodeGraph index is behind the
# code. CodeGraph's own git hooks normally keep it current, so this is a guard
# rail, not a scheduler — and a guard rail that speaks every session is one
# nobody reads.
#
# Deliberately shallow: it compares the index file's mtime against the newest
# tracked source file. That misses subtleties the CLI knows about, and catches
# the case that actually matters (hooks silently not firing).
set -u

command -v codegraph >/dev/null 2>&1 || exit 0

project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
cd "$project_dir" 2>/dev/null || exit 0
[ -d .git ] || exit 0

index=$(find "$project_dir" -name '*.codegraph*' -o -name 'codegraph.db' 2>/dev/null | head -1)
if [ -z "$index" ]; then
  echo "codegraph: installed but this repo has no index — run the codegraph-setup skill, or the codegraph rule will send the agent to a tool that can't answer."
  exit 0
fi

newest_source=$(git ls-files -z 2>/dev/null \
  | xargs -0 -r ls -t 2>/dev/null \
  | head -1)
[ -z "$newest_source" ] && exit 0

if [ "$newest_source" -nt "$index" ]; then
  echo "codegraph: index is older than '$newest_source' — re-index before relying on codegraph_explore."
fi
exit 0
