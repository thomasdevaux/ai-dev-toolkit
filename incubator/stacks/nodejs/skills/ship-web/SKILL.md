---
name: ship-web
description: Prepare a Node.js/web project for shipping — eslint, prettier, tsc, and tests are mandatory. Use when finishing, releasing, or deploying a web project or Node package.
when_to_use: Use when asked to "finish", "ship", "deploy", or "release" a Node/web project.
---

# Ship a web project

Before considering a Node.js/web project done, all of the following must
pass:

1. **Lint**: `npx eslint .` with zero unresolved issues.
2. **Format**: `npx prettier --check .` clean (or run `npx prettier --write .`
   and commit the result).
3. **Type-check**: `npx tsc --noEmit` clean (TypeScript projects).
4. **Tests**: the project's test command (e.g. `npm test`) passes. Add a
   test for new logic that doesn't already have coverage.
5. **Build**: `npm run build` succeeds without errors (informational
   output from the bundler is fine; treat any error exit code or emitted
   error diagnostic as a failure).

Do not report the project as "done" until all five checks pass — state
which ones you ran and their result.
