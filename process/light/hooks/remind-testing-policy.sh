#!/bin/bash
# SessionStart hook: reminds Claude of process/light's testing policy at the
# start of every session, since it's easy to forget mid-conversation and the
# rule only otherwise surfaces via testing-strategy.md when directly relevant.
echo "process/light reminder: any non-trivial new feature or bugfix needs at least one automated test covering its main path before it's considered done (see .claude/rules/testing-strategy.md)."
