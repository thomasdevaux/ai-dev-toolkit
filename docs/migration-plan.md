# Migration plan: ai-dev-toolkit → Agentic Software Kit v1.0.0

**Temporary.** This file lives on the `docs/redesign-vision` branch to carry
the work into fresh sessions; it is deleted (or folded into the new repo's
`docs/`) once v1.0.0 is tagged. The *what* and *why* are in
[`vision.md`](vision.md) — read it first; this file is only the *order*,
the *done* criteria and what a new session cannot guess.

## How to use this file in a new session

1. Read `docs/vision.md`, then this file.
2. Find the first step whose box is unchecked; do only that step.
3. When it is done (its "Done when" holds), tick it here, commit this file
   on `docs/redesign-vision` in the old repo, and stop for review.
4. Anything decided along the way that changes `vision.md` goes into
   `vision.md`, not here.

## Decisions still open

| Decision | Needed by | Default if nobody decides |
|---|---|---|
| Pilot project: CaliGrapHY or Commitment (both Go/Wails) | Step 5.1 | Commitment (smaller, already AGENTS.md-centred) |
| ~~GitHub repo~~ | — | Decided: private, `thomasdevaux/agentic-software-kit` |
| LSP: optional `lsp` module (`.github/lsp.json` for Copilot, doc for Claude, Serena for Vibe, `doctor` checks binaries) vs dropped | Step 2 (modules) | Proposed in session 2026-11-19, not confirmed |
| Final PyPI name (`agentkit` may be taken on public PyPI; irrelevant on the GitLab registry) | Step 4.3 | `agentkit` on GitLab, no public PyPI |

## Things a new session cannot guess

- **Do not clone or create test fixtures under `C:\Users\<name>\`**: Claude
  Code then ignores `AGENTS.md` (a parent `CLAUDE.md` wins). Use `C:\dev\`.
  The session scratchpad is under the user profile — fine for scripts,
  not for fixtures an agent must load.
- **Testing harness behaviour headlessly**: `claude -p ... --setting-sources
  project --strict-mcp-config --no-session-persistence` isolates from user
  rules and MCP (`--bare` needs an API key, not the subscription). Copilot:
  `copilot -p`; Vibe: `vibe -p`, launched from the repo root.
- **Windows**: copies, not symlinks; never `-ExecutionPolicy Bypass`;
  Python reading downloaded content runs with `-I`; on cp1252 consoles add
  `-X utf8`.
- **Serena 2.1** exposes one REPL tool unless started with
  `--agent-interface tools`; its app code is GPL-3.0-or-later.
- **The old repo keeps working** until step 6: consumer projects still
  depend on it. Never edit `.claude/` in the old repo by hand (it is sync
  output).
- Code-intelligence benchmark scripts were kept only in a session
  scratchpad (not durable). The method and numbers are in `vision.md`;
  rebuild from there if needed.

## Step 0 — Bootstrap the new repository

- [x] **0.1 Legacy snapshot.** `git archive` the old repo's `main` into a
  fresh directory `C:\dev\agentic-software-kit`, `git init`, one commit
  `Legacy: ai-dev-toolkit 0.0.1 snapshot`, tag `v0-legacy`. No history
  carried over (deliberate).
  *Done when*: `git log --oneline` shows exactly one commit, tagged.
- [x] **0.2 Remote.** Ask the maintainer, then `gh repo create` (see open
  decisions). Push `main` and the tag.
- [ ] **0.3 Clear the floor.** One commit removing the legacy tree from the
  working state (it stays in `v0-legacy`), adding the empty v1 layout:
  `README.md` (stub), `AGENTS.md` (the kit's own, skeleton per
  `project-context`), `CHANGELOG.md`, `pyproject.toml`, `src/agentkit/`,
  `catalog/{core,profiles,stacks,modules,community}/`, `tests/`, `docs/`,
  `.gitignore` (security rule list), `.pre-commit-config.yaml`.
  *Done when*: `uv run agentkit --version` prints `1.0.0.dev0`.

Packaging note: `uvx --from git+<repo>@<tag> agentkit` builds from the
repo, so `catalog/` must be shipped as package data (hatchling
`force-include` of `catalog` → `agentkit/catalog`), read at runtime through
`importlib.resources`. Test the built wheel, not the source tree.

## Step 1 — CLI skeleton (the core loop, end to end)

Goal: one profile + one stack rendered into a fixture project, with
ownership rules and tests. Content is minimal placeholder text; real
content is step 2.

- [ ] **1.1 Block model.** `block.yaml` schema (id, summary, status
  `stable|to-be-proven`, harnesses, detection markers, requires) and a
  loader that walks `catalog/`; the folder is the category, no manifest.
  Unit tests on valid/invalid blocks.
- [ ] **1.2 Project declaration.** `agentkit.yaml` schema (as in
  `vision.md`), validation with helpful errors; `agentkit.lock` format
  (kit version + every file written + its hash).
- [ ] **1.3 Renderer.** Pure function: (catalog, declaration) → planned
  file set, then a writer applying the three ownership categories:
  kit file (header "generated, do not edit"), managed block between
  `agentkit:begin` / `agentkit:end` (stop with an error if markers were
  removed), project file (create once from a template, never touch again).
  Pruning: files in the old lock but not in the new plan are deleted.
  `.agents/skills/` is the source; `.claude/skills/` a copy when `claude`
  is in `harnesses`.
- [ ] **1.4 Commands** `init` (detection → proposal → write
  `agentkit.yaml` → render; non-interactive flags for tests), `render`
  (deterministic, exit 1 if the tree would change — usable in CI),
  `update [--to X]` (bump + render + change summary).
- [ ] **1.5 Minimal content** to exercise it: `catalog/core` (security,
  language — real text, short), `catalog/profiles/app` (placeholder),
  `catalog/stacks/go` (placeholder skill + `.golangci.yml`).
- [ ] **1.6 Tests**: rendering snapshots (fixture project + declaration →
  expected tree, committed under `tests/snapshots/`), idempotence (render
  twice = no diff), managed block preserved around hand-written text,
  missing-marker refusal, pruning.

*Done when*: on a scratch git repo under `C:\dev\`, `uvx --from
<local path> agentkit init --profile app --stack go --harness claude,copilot,vibe`
produces `AGENTS.md` + `.agents/skills` + `.claude/skills` + `.golangci.yml`;
the canary check (step 1.7) passes; `pytest` green.

- [ ] **1.7 Canary check of the rendered output** in Claude Code, Copilot
  CLI and Vibe (the spike method in `vision.md`): each harness sees the
  managed block and the skills. Manual, recorded in the step's commit
  message.

## Step 2 — Content, block by block

Follow the triage table in `vision.md`. One branch/commit per block or
small group; each block gets `README.md` (3 sentences + what it writes),
`block.yaml`, `agents.md` (≤ 5 lines), skills.

- [ ] 2.1 `core`: security, language, commit-message-format, `agentkit`
  skill (how to use the kit from inside a harness).
- [ ] 2.2 `profiles/none`, `profiles/app` (doc map prohibitions,
  `project-docs` skill, `project-context` skill merged from init/audit,
  `desktop-app-architecture`, git workflow skill in two variants
  `mr` / `local-merge`). `profiles/embedded`: directory with a README
  saying "reserved", no content.
- [ ] 2.3 `stacks/`: go, rust, python, web-frontend, shared —
  `*-style` folded into `*-code-standards`, lint-enforceable prose removed,
  `build-and-disk.md` deduplicated if identical.
- [ ] 2.4 `community/`: caveman (keep `SOURCE.md` + `LICENSE`),
  session-report, statusline, codegraph (with its usage hint — measured:
  a tool without a hint is not used), serena (`--agent-interface tools`).
  Status `to-be-proven` where the triage says so.
- [ ] 2.5 `modules/`: gitlab (to be proven, portability work), lsp if
  confirmed.
- [ ] 2.6 Budget check: always-loaded `AGENTS.md` block for an app + go
  project measured and recorded in `vision.md` (target ~2–4k chars vs
  14,349 today).

*Done when*: `agentkit list` shows every block with status and harnesses;
catalog lint (step 3.5) green.

## Step 3 — Mechanics

- [ ] 3.1 Lint configs copied per stack; `doctor` flags competing configs
  (`[tool.ruff]` in `pyproject.toml` etc.).
- [ ] 3.2 pre-commit: managed block in `.pre-commit-config.yaml`, hooks
  per stack (`fast` tier), `commit-msg` (gitlint: format + no
  AI-attribution trailers), `pre-push` branch-name check (regex in
  `vision.md`); `init` runs `pre-commit install`.
- [ ] 3.3 `agentkit docs list / add / lint` (doc-map slots from templates).
- [ ] 3.4 `agentkit adr new / supersede / index`.
- [ ] 3.5 `agentkit doctor`: version lag, markers, hand-edited kit files,
  `AGENTS.md` links resolve, hooks active, detection suggestions,
  project under the user profile warning, Vibe-from-root hint, missing
  language-server binaries (if `lsp` module).
- [ ] 3.6 Catalog lint in the kit's own CI/tests: `block.yaml` schema,
  README present, `SKILL.md` frontmatter, always-loaded budget,
  `CATALOG.md` freshness, no secrets.

## Step 4 — GitLab (written on GitHub, validated after the move)

- [ ] 4.1 CI proposals as text under `ci/` (pre-commit `--all-files`,
  secret detection, `agentkit render` check, non-blocking "newer kit" job,
  sandbox-branch refusal).
- [ ] 4.2 `agentkit doctor --gitlab` (read-only, `glab api`): protected
  branches, approvals, push rules, each gap with a one-line why.
- [ ] 4.3 Release pipeline: tag → build → publish to the GitLab PyPI
  registry + release; protected tags; `CODEOWNERS`.
- [ ] 4.4 `CATALOG.md` generated, CI-checked.

Marked "unvalidated" in `CHANGELOG.md` until run on the self-hosted GitLab.

## Step 5 — Pilot

- [ ] 5.1 Pick the pilot (open decision). On a branch of the pilot:
  `agentkit init --migrate` — reads `.claude/.toolkit-sync-state`, deletes
  exactly its `files`, removes the old `settings_patch` keys from
  `.claude/settings.json` (hooks, `attribution`, `includeCoAuthoredBy`,
  `enabledPlugins` entries, `companyAnnouncements`), moves competing tool
  configs, removes the `CLAUDE.md` pointer, then a normal `init`.
- [ ] 5.2 Work on the pilot for real for a few sessions with 2–3 harnesses
  (Claude, Copilot, Vibe). Log friction in the kit's issues, fix, re-render.
- [ ] 5.3 `agentkit user install --migrate` on the maintainer's machine
  (cleans what `common-rules-user` etc. put in `~/.claude/`).

*Done when*: the pilot's gates pass, its `doctor` is clean, and the
maintainer would hand it to a teammate as is.

## Step 6 — v1.0.0

- [ ] 6.1 Split `vision.md` per its "Handover" section (ADRs,
  `architecture.md`, short vision); `README.md`, cut-down
  `maintaining.md`, the 15-minute tutorial (run it once as a test).
- [ ] 6.2 Tag `v1.0.0`; migrate the other consumer projects (one MR each).
- [ ] 6.3 Archive the old repository; delete this file.
