#!/bin/bash
# PreToolUse hook (matcher: Bash): refuses `git commit` while HEAD sits on an
# integration branch. This is the one half of git-workflow-app a script can
# decide without judgment — "never push without acceptance" and "run the tests
# first" both need a human, so they stay in the rule and the skill.
#
# Deliberately self-contained: unlike self-check's hooks it needs no toolkit
# checkout, only git, so it does not go through resolve-toolkit-root.sh. One
# less network path hung off a tool call.
#
# There is no override, and that is the design. An agent told "commit on main
# anyway" cannot: exit code 2 is final. The escape is the user running the
# command themselves, which is explicit, takes a second, and leaves the call
# with the human — exactly the split intended. Don't add an env-var bypass:
# a prohibition the constrained party can switch off constrains nothing.
#
# Known gaps, accepted rather than papered over. It matches a substring of the
# raw payload, so `git -C <path> commit` and a `git commit` reached through a
# script or an alias slip past; and it only sees git run through the Bash tool,
# never what the user types in their own terminal. It guards the agent's common
# path, not the repository.
set -u

PAYLOAD="$(cat)"

# Cheap gate first: this fires on every Bash call in every session.
case "$PAYLOAD" in
    *'git commit'*) ;;
    *) exit 0 ;;
esac

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

# Not a repository, or git unavailable: nothing to guard, stay out of the way.
git -C "$PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1 || exit 0

# A conflicted merge is finished with a plain `git commit`, and landing a
# branch onto the integration branch is exactly what the rule permits.
GIT_DIR="$(git -C "$PROJECT_DIR" rev-parse --git-dir 2>/dev/null)"
[ -f "$GIT_DIR/MERGE_HEAD" ] && exit 0

BRANCH="$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)"

case "$BRANCH" in
    main|master|develop) ;;
    *) exit 0 ;;
esac

# Exit code 2 blocks the call and returns stderr to the agent. Silent on every
# other path above, per the toolkit's hook invariant.
cat >&2 <<EOF
Refused: committing on '$BRANCH', which git-workflow-app protects.

Uncommitted work carries over to a new branch — nothing is lost:

  git checkout -b <type>/<slug>

Types: feat, fix, test, docs, chore, sandbox. Propose the name to the user
before creating it. The git-workflow-app skill has the naming rules.
EOF
exit 2
