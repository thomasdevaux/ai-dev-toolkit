---
name: frontend-code-standards
description: Set up or repair the team's web front-end quality tooling in a package - Prettier, ESLint (typescript-eslint, React hooks), tsc and Vitest, with the npm scripts that run them. Use when a front end (React on Tauri or Wails, or any package.json project) has no Prettier or ESLint configuration, has one that diverges from the team's, or carries a backlog of findings to adopt it on.
---

# Front-end Code Standards

Install the team's front-end tooling in the package that holds the front end
(`apps/desktop/` in a Tauri app, `frontend/` in a Wails app, `apps/<name>/`
in a monorepo), or bring an existing setup back in line. The day-to-day rules —
run the tools, how to silence a finding legitimately — live in
`rules/web-frontend-style.md` and load on their own; this skill is the setup procedure.
The React structure itself (`ipc/`, `bindings/`, server state) is the
architecture skill's `react-conventions.md`, not this one.

## The stack, and why

| Job | Tool | Script |
|---|---|---|
| Format | Prettier | `format` (`prettier --write .`), `format:check` (`prettier --check .`) |
| Lint | ESLint + typescript-eslint + eslint-plugin-react-hooks | `lint` (`eslint .`) |
| Types | `tsc` | `typecheck` (`tsc --noEmit`) |
| Test | Vitest | `test` (`vitest run`) |

**Every tool is a pinned devDependency, run through a script.** `npx prettier`
then resolves the project's copy; a globally installed or downloaded one
formats with whatever version it happens to be, and two machines disagree.
The CI gate calls the same scripts a developer does.

**Prettier stays default on purpose**, like rustfmt and gofmt: its value is
that every front end looks the same. The reference sets one option,
`endOfLine: "auto"`: with Git's `core.autocrlf` on (the Windows default) a
checkout has CRLF line endings, and Prettier's default `lf` fails every file.
`.editorconfig` still makes new files LF. A project that pins line endings
in `.gitattributes` (`* text=auto eol=lf`) can drop the option.

**ESLint runs type-aware.** `strictTypeChecked` catches floating promises,
unsafe `any` flows and needless conditions, which a syntax-only config cannot
see. It costs a slower lint — `eslint --cache` for the inner loop is the
answer, not a weaker preset.

**The reference relaxes a few strict rules on purpose**, each commented in
`references/eslint.config.js`: async event-handler props
(`no-misused-promises` attributes), numbers in template literals,
arrow-shorthand void calls (`onClick={() => setOpen(false)}`), `_`-prefixed
unused bindings, plain-object rejections inside `src/ipc/` (the backend's
typed error), and in test files the `require-await` / `no-unsafe-*` family
and non-null assertions (`items[0]!`: an absent value fails the test anyway).
These are React and Vitest idioms the strict preset reports in every
project; they make up most of a strict backlog and catch no bug. They are not a licence for more: anything beyond them is still a
project deviation, recorded as a comment next to the setting.

**The `ipc/` boundary is enforced, not just documented.** A
`no-restricted-imports` rule lets only `src/ipc/` import the generated
bindings — the rule `react-conventions.md` §2 calls the one that matters most.

## Procedure

### A package with no configuration

1. Install the tools as devDependencies:
   `npm install -D prettier eslint @eslint/js typescript-eslint eslint-plugin-react-hooks typescript vitest`.
   Check them first per the security rule (`npm audit`). Behind the
   corporate proxy, npm needs the machine-local setting in
   `references/corporate-proxy.md`. Pin `@types/node` to the major of the
   Node runtime in use, not the newest one.
2. Copy `references/prettierrc.json` to `.prettierrc.json`,
   `references/prettierignore` to `.prettierignore`, and
   `references/eslint.config.js` to `eslint.config.js`. Adjust the generated
   bindings path and the backend folder (`src-tauri`, the Go module) in both
   ignore lists if the project differs.
3. Add the scripts of the table above to `package.json`. In a workspace, add
   root scripts that forward to the front-end package
   (`npm run lint --workspace=<package>`), so the gate calls one place.
4. Copy `references/editorconfig.ini` to the project root as `.editorconfig`
   if there is none. It is the same baseline in every stack. If there is one,
   diff it against the reference and report the differences rather than
   overwriting it.
5. TypeScript: from TypeScript 6, `tsc` no longer loads every installed
   `@types` package — list them in `tsconfig.json`
   (`"types": ["node"]`, plus `"vitest/globals"` if the tests use globals).
   Turn on `noUncheckedIndexedAccess`: without it an index read is typed as
   always present, and `no-unnecessary-condition` then reports the very
   guard that protects it.
   Include `vite.config.ts` **and** `vitest.config.ts` in
   `tsconfig.node.json`: a config file outside every tsconfig is reported by
   the type-aware lint, and `allowDefaultProject` is only the workaround.
6. Run `npm run format`, and commit that as one mechanical commit, separate
   from any behaviour change.
7. Run `npm run lint` and `npm run typecheck` and deal with the output per the
   section below.
8. Wire `format:check`, `lint`, `typecheck` and `test` into the project's gate
   script, next to the backend's tools, and the changed-files variant
   (`prettier --check <files>`, `eslint --cache`) into its inner loop if it
   has one.

### A package that already has a configuration

Do not overwrite it. Diff it against the reference and report the
differences, grouped:

- **Prettier options beyond `endOfLine`** — ask why. Each one is a
  preference the team traded uniformity for.
- **A weaker ESLint preset** (`recommended` instead of `strictTypeChecked`,
  or no type information) — the most common divergence; sequence it per the
  section below.
- **No bindings import restriction** — add it; it is cheap and it guards the
  architecture. An app without generated bindings uses the alternative block
  commented at the end of `references/eslint.config.js`: it restricts
  `invoke` itself to the IPC module.
- **Rules the project enables that the reference does not** — a candidate to
  propose upstream, not to delete.

Record deliberate differences as comments in `eslint.config.js` next to the
setting.

### Adopting on a package with a backlog

The failure mode is a first run reporting hundreds of findings, which get
ignored wholesale. Instead:

1. Land the Prettier pass first, alone, as one mechanical commit.
2. Enable `recommendedTypeChecked` and clear it before moving to
   `strictTypeChecked`. Clear `react-hooks` findings early: they are bugs
   (stale closures, effects that never re-run), not taste.
3. Never adopt by adding `/* eslint-disable */` to files or turning rules
   off globally. That records the backlog as permanent.
4. Run `npm run typecheck` after every `eslint --fix`. Removing an assertion
   that `no-unnecessary-type-assertion` calls redundant can be right for
   ESLint and still break `tsc`, typically where the assertion narrowed a
   string to a literal union.

## Changing the standard

The reference configuration is the team's, not the package's. A rule worth
enabling everywhere is changed in
`tech-stacks/web-frontend/skills/frontend-code-standards/references/` in the
toolkit checkout, and reaches projects at their next sync.
