---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.css"
---

# Web front-end code standards

The mechanical part is enforced by tooling, not by this file: Prettier for
formatting (code, CSS, JSON, Markdown of the front-end package), ESLint for
lint, `tsc` for types. Their configuration is the actual standard —
`frontend-code-standards` holds the ready-to-copy version and the procedure
for adopting it. If the package has no Prettier or ESLint configuration yet,
say so once and offer to run that skill.

What tooling cannot decide, and this file does:

- **Run the tools once per task, not per edit.** While working: `prettier
  --write` on the files you changed and the targeted `vitest run <path>`. When
  the task's code is finished, and unless a project gate runs them
  (`verification-tiers`): `eslint`, `tsc --noEmit` and the whole test suite. A
  finding is either fixed or silenced with a reason — never left reported.
  Use the project's own scripts (`format:check`, `lint`, `typecheck`,
  `test`) when it has them: they pin the version and the file set.
- **Prettier is the project's own copy.** `npx prettier` resolves the
  devDependency in `node_modules`; if it would download one instead, the
  package is not set up — say so rather than formatting with a stray version.
- **Silencing needs a named rule and a why.** `// eslint-disable-next-line`
  alone is not acceptable; `// eslint-disable-next-line
  react-hooks/exhaustive-deps -- runs once, the dialog is keyed by its
  device` is. Never a file-wide `/* eslint-disable */`. For
  `react-hooks/set-state-in-effect`, try a `key` or a value derived during
  render first; the disable is right when the effect resets local state on a
  prop change or mirrors a store that has no subscription API.
- **Generated files are neither formatted nor linted.** The backend's
  bindings (`src/bindings/`, Wails' `bindings/`) and build output stay in `.prettierignore` and
  the ESLint `ignores`; a hand edit there is lost on the next generation.
- **No `any` at the `ipc/` boundary**, and no `as` cast to quiet the type
  checker there — that is where generated types earn their keep.

Changing a rule of the shared configuration is a team decision, not a
per-package one: propose it against the toolkit's `frontend-code-standards`
reference rather than editing one package's configuration alone.
