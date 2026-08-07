#!/bin/bash
# SessionStart hook, two jobs:
#
#  1. CodeGraph installed — says something ONLY when the index is behind the
#     code. CodeGraph's own git hooks normally keep it current, so this is a
#     guard rail, not a scheduler, and a guard rail that speaks every session
#     is one nobody reads.
#  2. CodeGraph absent — suggests installing it, but only on a repository big
#     enough for the index to repay its cost, and only a handful of times ever
#     (see the nudge section). Without this the whole thing was a closed loop:
#     the rule stays silent when the tool is missing, this hook exited on the
#     same condition, and the skill is disable-model-invocation — so the one
#     lever token-economy.md calls the highest-impact of the set was
#     undiscoverable unless you already had it.
#
# Deliberately shallow: it compares the index file's mtime against the newest
# tracked source file. That misses subtleties the CLI knows about, and catches
# the case that actually matters (hooks silently not firing).
set -u

project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
cd "$project_dir" 2>/dev/null || exit 0
# Not `[ -d .git ]`: in a worktree or a submodule, .git is a *file*, and the
# check would then silently never run.
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# --- CodeGraph not installed: suggest it, rarely, and only where it pays ----
#
# Threshold is on *indexable* sources, never on the file count: a repo that is
# mostly markdown and YAML gets no benefit from a code graph, and the first
# false positive is what teaches everyone to ignore this hook. Extensions are
# copied from the languages CodeGraph actually supports — see the skill's
# provenance block; suggesting the tool for a language it can't read is worse
# than saying nothing.
#
# 300 is the point where grep stops answering "who calls X" in one shot. Note
# it bites about twice as early on C, where headers roughly double the count
# for the same amount of code — deliberate, since symbol navigation is worth
# most exactly there.
NUDGE_THRESHOLD=300
NUDGE_MIN_DAYS=30
NUDGE_MAX_COUNT=3
SOURCE_EXT='\.(c|h|cpp|hpp|cc|cs|py|js|jsx|mjs|ts|tsx|go|rs|java|kt|kts|rb|php|swift|scala|dart|lua|m|mm|vb|erl|sol)$'

if ! command -v codegraph >/dev/null 2>&1; then
    sources=$(git ls-files 2>/dev/null | grep -Ec "$SOURCE_EXT") || sources=0
    [ "$sources" -ge "$NUDGE_THRESHOLD" ] || exit 0

    # Keyed on the repo path so each project nags on its own schedule, hashed
    # only to get a filename-safe key.
    state_dir="$HOME/.ai-dev-toolkit/codegraph-nudge"
    mkdir -p "$state_dir" 2>/dev/null || exit 0
    key=$(printf '%s' "$project_dir" | cksum | cut -d' ' -f1)
    state_file="$state_dir/$key"

    count=0
    last=0
    if [ -f "$state_file" ]; then
        read -r count last < "$state_file" 2>/dev/null || exit 0
    fi
    # Declining is never reported back to us, so a bounded number of asks is
    # the only way to read silence as an answer.
    [ "$count" -lt "$NUDGE_MAX_COUNT" ] || exit 0
    now=$(date +%s)
    [ $((now - last)) -ge $((NUDGE_MIN_DAYS * 86400)) ] || exit 0
    echo "$((count + 1)) $now" > "$state_file"

    echo "ACTION: this repository has $sources indexable source files and no CodeGraph index, so symbol-level questions here cost a file-by-file search. Before addressing anything else, ask the user via the AskUserQuestion tool - question text exactly \`Install CodeGraph on this repository?\`, options \`Install now\`, \`Tell me more first\`, \`Not now\`. On \`Install now\`, follow the codegraph-setup skill, which states what gets installed and where before touching anything. On \`Tell me more first\`, summarise that skill's \"What it actually installs\" table and ask again in plain text. On \`Not now\`, drop it and do not raise it again this session. Then proceed with whatever the user asked."
    exit 0
fi

# --- CodeGraph installed: warn only when the index is behind the code -------

# Pruned rather than a bare walk: an unbounded find over node_modules/,
# .venv/ or target/ costs seconds on a big repo, at every session start,
# blocking.
index=$(find "$project_dir" \
  \( -name .git -o -name node_modules -o -name .venv -o -name venv \
     -o -name target -o -name build -o -name dist -o -name __pycache__ \) -prune \
  -o \( -name '*.codegraph*' -o -name 'codegraph.db' \) -print 2>/dev/null \
  | head -1)
if [ -z "$index" ]; then
  echo "codegraph: installed but this repo has no index — run the codegraph-setup skill, or the codegraph rule will send the agent to a tool that can't answer."
  exit 0
fi

# Asked as "is any tracked file newer than the index", not as "find the
# newest tracked file, then compare": piping the list into `xargs ... ls -t`
# breaks past ARG_MAX, since xargs splits it and each `ls -t` then sorts only
# its own batch. A shell loop has no such limit and stops at the first hit,
# so the common case doesn't even walk the whole list.
stale=""
while IFS= read -r -d '' f; do
  if [ "$f" -nt "$index" ]; then
    stale="$f"
    break
  fi
done < <(git ls-files -z 2>/dev/null)

if [ -n "$stale" ]; then
  echo "codegraph: index is older than '$stale' — delegate to the codegraph-reindex agent before relying on codegraph_explore; an empty answer after that means fall back to grep."
fi
exit 0
