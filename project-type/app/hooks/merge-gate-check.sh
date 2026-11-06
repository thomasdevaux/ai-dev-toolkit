#!/bin/bash
# SessionStart hook: says so when nothing stands between a local merge and the
# integration branch. Git hooks don't travel with a clone, so the merge gate can
# be absent without anything failing: that silent state is what this reports.
#
# It warns and blocks nothing. CI is detected by its configuration file alone,
# which can't tell whether the CI is required before landing; `git-workflow-app`
# makes that call, this only stays out of the way. Silent when the check passes.
set -u

cd "${CLAUDE_PROJECT_DIR:-$PWD}" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

HOOKS="$(git rev-parse --git-path hooks)"
[ -x "$HOOKS/pre-merge-commit" ] && exit 0

if [ -f .githooks/pre-merge-commit ]; then
    echo "merge gate: .githooks/pre-merge-commit is not active in this clone, so a merge runs no gate. Fix: git config core.hooksPath .githooks"
    exit 0
fi

for ci in .github/workflows .gitlab-ci.yml azure-pipelines.yml bitbucket-pipelines.yml Jenkinsfile .gitea/workflows .forgejo/workflows; do
    [ -e "$ci" ] && exit 0
done

echo "merge gate: this project has no CI and no pre-merge-commit hook, so nothing gates a merge. The git-workflow-app skill sets one up."
exit 0
