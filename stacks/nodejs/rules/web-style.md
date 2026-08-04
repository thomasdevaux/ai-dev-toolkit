---
paths:
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.ts"
  - "**/*.tsx"
---

# Node.js / web style

- ESLint and Prettier must both pass cleanly before committing; do not
  disable a rule inline without a comment explaining why.
- TypeScript projects run with `strict: true` in `tsconfig.json`. Do not
  weaken strictness to silence an error — fix the underlying type issue.
- No `any` without a comment explaining why a precise type isn't possible.
- Use `const`/`let`, never `var`.
- Prefer named exports over default exports for anything imported in more
  than one place, so renames and refactors stay traceable.
- Environment-specific config (API URLs, feature flags) comes from
  environment variables, never hardcoded per-environment branches in code.
