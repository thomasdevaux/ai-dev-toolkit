# Vision: the next version of the kit

Status: **brainstorming** — decisions below are provisional until the
harness spike (see "Open questions") confirms the foundations. Nothing in
the current toolkit has been changed yet.

## Why a redesign

The kit is moving from a single-user tool to a team of ~10 people learning
agentic development, on a self-hosted GitLab Premium, on Windows, and its
maintenance will be handed over soon. That changes the priorities:

- **Simple enough to hand over.** Two documentation levels: a short human
  README per block, detailed instructions for the agent in the skill itself.
- **Multi-harness by design.** First class: **Claude** (Claude Code CLI and
  VS Code's Claude harness), **Copilot** (Copilot CLI and VS Code's Copilot
  harness), **Mistral Vibe**. Best effort: Codex, OpenCode, Pi, Gemini CLI,
  Cursor. VS Code is a host, not a target of its own (see "Standards
  first"). The provider isn't
  chosen yet and must stay changeable mid-project, so **stay as close to
  the standards as possible**, even at the cost of harness power features.
- **Visible, not opaque.** Users are learning; they must be able to open a
  file and ask a question about it.
- **Deterministic where possible.** "The skill says when and why, the
  script does the how." Shared, executable methods also make cheaper
  models usable without losing quality.
- **Less overlap between user and project scope**, and room for personal
  skills.

## What a consumer of the kit wants (kept from today)

Stack know-how, project discipline (doc map, ADRs, requirements — heavily
used on the Go/Wails and Rust/Tauri tools), pedagogy, guardrails.
Updating a project to the latest kit stays easy, and **always goes through
a commit and a merge request**.

## Decisions so far

### Distribution

- **Copy and commit** stays the model (the only one that is visible, goes
  through an MR, and works for every harness). Submodules, plugins and
  user-global installs were considered and rejected.
- **One repository**, better organised.
- **The kit is a Python package (uv) that embeds its own content**: the
  tool version is the content version. Run with
  `uvx agentkit@1.4.0 <cmd>` from the GitLab PyPI registry, or
  `uvx --from git+<kit repo>@v1.4.0 agentkit <cmd>` from a git tag — both
  supported. No install script, no cache checkout.
- `agentkit` is a placeholder name.

### Standards first

Spike results, tested 2026-11-18 with canary fixtures (no tools allowed,
answers from loaded context only):

| | Root `AGENTS.md` | Nested `AGENTS.md` (run from `sub/`) | `.agents/skills` | `.claude/skills` | `.github/skills` | Same skill in two dirs |
|---|---|---|---|---|---|---|
| Claude Code 2.1.327 | ✅ (see pitfall) | ✅ root + sub | ❌ | ✅ | ❌ | — |
| Copilot CLI 1.0.112 | ✅ | ✅ root + sub | ✅ | ✅ | ✅ | Deduplicated by name; `.agents` won (observed once, this version) |
| Mistral Vibe 2.25.4 | ✅ | ⚠️ only the launch dir's, root lost | ✅ (launched from root) | ❌ | ❌ | — |
| VS Code native agent | not tested yet | | | | | |

User level (tested): Copilot reads `~/.copilot/skills` and
`~/.agents/skills`, not `~/.claude/skills`; Vibe reads `~/.agents/skills`
and `~/.vibe/skills`. So `~/.agents/skills` covers Copilot and Vibe, and
only Claude needs the copy to `~/.claude/skills`.

**VS Code is a host, not a harness** (docs dated 2026-11-18,
[agent harnesses](https://code.visualstudio.com/docs/agents/run/agent-harnesses)).
Its chat runs one of: **Copilot** (the Copilot SDK runtime shared with
Copilot CLI; the docs warn it "does not imply identical tools, models,
permissions, or customizations"), **Claude** (the Claude Agent SDK, with
Claude Code's loading rules), **Codex**, or **Local** — the legacy native
harness, **deprecated and removed by February 2027**. So "VS Code native" is
not a target. **Inference, not tested**: VS Code users are covered by the
Copilot and Claude rows, because the runtimes are shared; nobody has run
the canary fixture inside VS Code yet (no subscription available). Known gap: the Copilot
harness ignores `~/.claude/skills` (vscode issue #343749, open) — consistent
with putting personal skills in `~/.agents/skills`.

Copilot's cloud coding agent only works on GitHub repositories, so it is out
of scope on the self-hosted GitLab.

Best-effort harnesses (documentation, not tested):

| | Context | Project skills | User skills | Name collision |
|---|---|---|---|---|
| Pi 1.5 (local docs) | `AGENTS.md` (or `CLAUDE.md`) from cwd and parents, concatenated | `.pi/skills`, `.agents/skills` (up to repo root) | `~/.pi/agent/skills`, `~/.agents/skills` | First found wins, with a warning |
| OpenCode | `AGENTS.md` walking up; `CLAUDE.md` fallback (single source) | `.opencode/skills`, `.claude/skills`, `.agents/skills` | `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` | Not documented — reads both our dirs |
| Codex CLI | `AGENTS.md` chain root → cwd | `.agents/skills` | `~/.agents/skills` | — |
| Gemini CLI | `GEMINI.md`; `AGENTS.md` via `context.fileName` | `.gemini/skills` (`.agents/skills` disputed) | `~/.gemini/skills` | — |
| Cursor | `AGENTS.md` | `.cursor/skills` (`.agents/skills` disputed) | `~/.cursor/skills` | — |

`AGENTS.md` + `.agents/skills` is the convergence point; Claude Code is the
only first-class exception, hence the `.claude/skills` copy.

- `AGENTS.md` is the context file, **no `CLAUDE.md` pointer**. Pitfall:
  Claude Code ignores `AGENTS.md` as soon as any `CLAUDE.md` exists in the
  working directory or a parent. In the spike, a fixture under
  `C:\Users\<name>\` lost its `AGENTS.md` (probable cause:
  `~/.claude/CLAUDE.md` counting as a parent's), while the same fixture
  under `C:\dev\` loaded it. Team convention: **projects are never cloned
  under the user profile**; `agentkit doctor` warns when one is.
- `.agents/skills/` is the source location; a **generated copy** goes to
  `.claude/skills/` until Claude Code reads `.agents/skills`. Copies, not
  symlinks (Windows). Copilot deduplicates the two, so no double listing.
- **No nested `AGENTS.md`** in the design: harnesses disagree on them.
- **Vibe must be launched from the repository root** (user doc, and a
  `doctor` hint).
- Path-scoped rules (`python-style` etc.) have no common standard: their
  content is **folded into the `<stack>-code-standards` skills**, and what a
  linter configuration can enforce leaves the prose entirely.

### What lands in a consumer project

```
agentkit.yaml          # the declaration — the only kit file edited by hand
agentkit.lock          # generated: version + files written (for pruning)
AGENTS.md              # project-owned, plus a kit-managed block
.agents/skills/        # generated
.claude/skills/        # generated copy for Claude Code
.pre-commit-config.yaml  # project-owned, plus a kit-managed block
lint configs           # copied by the kit (.golangci.yml, ruff.toml, ...)
docs/                  # project-owned
```

```yaml
kit_version: 1.4.0
profile: app                 # none | app | embedded (reserved, not yet available)
stacks: [go, web-frontend]   # proposed by detection at init
modules: [gitlab]
community: [caveman]
harnesses: [claude, copilot, vibe]
git:
  integration: mr            # mr | local-merge
```

- `agentkit init` detects stacks and writes the file; the file is the
  source of truth afterwards. On `update`, detection only *suggests*
  ("`Cargo.toml` found but `rust` not declared").

**Ownership rule — three categories, nothing else:**

| Category | Examples | What `update` does |
|---|---|---|
| Kit file (header: "generated, do not edit") | skills, `.golangci.yml`, `ruff.toml` | Rewrites it |
| Managed block in a project file | `AGENTS.md`, `.pre-commit-config.yaml`, `Cargo.toml` `[lints]`, `.gitignore` entries | Replaces only between `agentkit:begin` / `agentkit:end` markers; stops if markers are missing |
| Project file | `docs/`, `README.md`, code, `.gitlab-ci.yml` | Never touches it (may create once from a template, on request) |

A local edit to a kit file is overwritten; the loss shows in the diff.
Customisation goes in `AGENTS.md` outside the block, or in project-owned
skills.

**Tool configurations**: a configuration the kit owns lives in the tool's
own standalone file whenever the tool supports one (`ruff.toml`,
`mypy.ini`, `.golangci.yml`, `rustfmt.toml`, `eslint.config.js`). A managed
block is used only when the tool has no standalone file (`Cargo.toml`
`[lints]`). A competing configuration in a shared file — e.g.
`[tool.ruff]` in `pyproject.toml`, which `ruff.toml` silently overrides —
is flagged by `doctor`, and `init` / `init --migrate` propose moving it.

### The `AGENTS.md` managed block

The kit puts **only prohibitions and pointers** there. Always-loaded
content today, for an app-profile project (common, context-quality, app and
self-check rules): **14,349 characters, measured**. Target: ~2–4k, an
estimate to be checked against the real v1 output. The detail
lives in skills, so an update of e.g. the doc map almost always changes a
skill file, not `AGENTS.md`.

### Updating a project

- `agentkit update` **regenerates only** — no branch, commit or MR. It can
  happen on any branch; recommended as its own commit
  (`chore: update agentkit 1.3 → 1.4`).
- "A newer kit is available" is reported by `agentkit doctor` and by a
  **non-blocking CI job** on merge requests. Renovate (automatic bump MRs)
  is documented for later.

### Guardrails move out of the harness

| Level | What | Role |
|---|---|---|
| Git, local | **pre-commit** framework (Python, fits uv); config shipped by the kit, activated by `agentkit init` / checked by `doctor` | Fast feedback for everyone, human or any agent |
| GitLab CI | Same pre-commit config run with `--all-files`, secret detection, stack checks | Catches anyone whose local hooks aren't active |
| GitLab settings | Protected branches, MR approvals, push rules (branch-name regex, no `Co-Authored-By`, secret files) | Unbypassable |

- Harness hooks (`git-branch-guard`, attribution settings) are dropped for
  guardrails.
- CI jobs are, for now, a **text proposal** in the kit, not deployed. Later:
  `include: project: <kit> ref: <tag>`.
- `agentkit doctor --gitlab` reads (never writes) the GitLab settings via
  `glab api` and reports gaps, each with a one-line "why".
- Alternatives considered for local hooks: native `core.hooksPath`,
  `prek` (pre-commit compatible, kept as an exit), `lefthook`, `husky`.

### Git workflow (app profile)

- Two variants selected by `git.integration`: `mr` and `local-merge`.
  Common rules are enforced by tooling; each skill variant keeps only its
  own procedure (~2k each instead of 9k).
- Branch types `feat fix test docs chore`, plus **`sandbox/<user>/<topic>`**
  (user = local part of `git config user.email`), which never merges —
  enforced by a CI job failing any MR from `sandbox/`.
- Branch-name push rule:
  `^((feat|fix|test|docs|chore)/[a-z0-9-]+|sandbox/[a-z0-9._-]+/[a-z0-9-]+)$`

### Mechanical over prose ("as much as possible")

| Today | Next |
|---|---|
| Skill tells the agent how to write lint configs | Kit copies the config files; the skill keeps adoption on a backlog |
| `write-adr` numbering, `INDEX.md`, supersede chains | `agentkit adr new / supersede / index` |
| `init-project-docs`, on-hold stub files | `agentkit docs list / add` — slots created on demand from templates, no stubs |
| `docs-lint` agent, `adr-cleanup` mechanics, `context-check` hook | `agentkit lint` / `doctor`, also in pre-commit and CI |
| Commit message format | `commit-msg` hook (e.g. gitlint) |
| Branch naming | Push rule + `pre-push` |
| `verification-tiers` | Standard `fast` / `full` task names; pre-commit runs `fast`, CI runs `full` |
| `check.ps1` architecture gates | Also run in pre-commit or CI |

### Kit repository layout

```
README.md  AGENTS.md  CHANGELOG.md  CATALOG.md (generated, CI-checked)
catalog/
  core/  profiles/{none,app,embedded}/  stacks/{python,rust,go,web-frontend,shared}/
  modules/   # opt-in, validated
  community/ # opt-in, not validated or "to be proven"
src/agentkit/  ci/  docs/  handbook/  tests/
```

- **No central manifest**, includes, tiers or choice-groups: the folder is
  the category. `CATALOG.md` is the one-glance human index (referenced from
  the team wiki).
- `incubator/` and `suggested/` merge into `community/`.

Every block has the same shape:

```
README.md     # human: three sentences + what it puts in your project
block.yaml    # id, one-line summary, status (stable | to-be-proven),
              # compatible harnesses, detection markers
agents.md     # ≤ 5 lines injected into the AGENTS.md managed block
skills/       # standard skills (SKILL.md + scripts/ + references/)
files/        # copied as-is
precommit.yaml
harness/<name>/  # optional harness-specific extras, marked as such
```

### Commands

| Command | Role |
|---|---|
| `agentkit init` | Detect, ask the profile, write `agentkit.yaml`, render, activate pre-commit |
| `agentkit update [--to X]` | Bump and regenerate; print a change summary |
| `agentkit render` | Regenerate at the pinned version (deterministic, for CI) |
| `agentkit doctor [--gitlab]` | Version lag, markers, hand-edited kit files, `AGENTS.md` checks, hooks active, detection suggestions, GitLab settings |
| `agentkit list / add / remove` | Catalog with harness compatibility; add or remove a block |
| `agentkit docs list / add / lint` | Doc-map slots |
| `agentkit adr new / supersede / index` | ADR mechanics |
| `agentkit user install` | Optional "outside a project" baseline and user tooling; never touches personal skills |

### Content triage

Criteria: real use or identified need (otherwise "to be proven", kept with
a warning); not already done by a tool; portable across the four harnesses;
explainable in three sentences to a beginner.

| Block | Verdict |
|---|---|
| `security`, `language` | Keep, shortened, in the minimal baseline |
| `project-type-profile` rule | Replaced by `agentkit.yaml` + `init` |
| `commit-message-format` | Keep; attribution ban moves to `commit-msg` hook + push rule |
| `desktop-app-architecture` | Move from common to the app profile |
| CodeGraph (rule, skill, agent, hook) | Community module, opt-in (measured: speed, not accuracy or cost) |
| `caveman`, `session-report`, statusline | Community / optional user tooling |
| LSP plugins | Not in core (Claude-only, unused without a hint). Optional `lsp` module proposed, undecided — see `migration-plan.md` |
| `project-context` rule, `init-` / `audit-project-context` | Rule → two lines; skills merged into one `project-context` skill |
| `context-check`, `codegraph-freshness`, `git-branch-guard` hooks | Replaced by `doctor`, pre-commit, CI |
| `/toolkit-*` commands, auto-apply rule, `resolve-toolkit-root`, `companyAnnouncements` | Replaced by the CLI + one portable `agentkit` skill |
| `no-project-type` rule | Three lines in the managed block |
| `embedded-fccu` stub | Removed; `embedded` stays reserved in the design |
| `docs-map`, `requirements`, `adr`, `testing-strategy` rules | Prohibitions into the managed block, the rest into a `project-docs` skill. Project documents (`docs/testing-strategy.md` etc.) are unchanged |
| `verification-tiers` | Mostly enforced by pre-commit / CI; one sentence remains |
| `git-workflow-app` | Simplified, two variants (see above) |
| `docs-lint` agent | Replaced by a script |
| `audit-docs` + `adr-cleanup` | Merged; mechanics to the script |
| `write-adr`, `init-project-docs` | Keep, backed by `agentkit adr` / `docs` |
| `improve-architecture`, `frontend-feedback` | Keep, "to be proven" |
| `*-style` rules | Folded into `*-code-standards`; lint-enforceable parts removed |
| `*-code-standards`, `*-desktop-architecture`, `shared/` | Keep; `build-and-disk.md` deduplicated if confirmed identical |
| `frontend-design`, GitLab official plugin, `skill-creator` | Removed (Claude-only plugins; a doc line at most) |
| GitLab workflow skills + `gitlab_tool.py` | Optional module, "to be proven", needs portability work (`allowed-tools`, `$CLAUDE_PROJECT_DIR` paths) |

### Personal skills and community

```
 PERSONAL (machine)       COMMUNITY (kit)              CORE (kit)
 ~/.agents/skills/   →    catalog/community/     →     catalog/modules|core|stacks/
```

- **Personal**: written in `~/.agents/skills` (the standard user location).
  `agentkit user install` only copies them to the harnesses that don't read
  it (e.g. `~/.claude/skills`); the kit never reads, judges or edits them.
- **Personal → community**: `agentkit share <path>` scaffolds the block
  (README, `block.yaml`) on a kit branch. CI checks the form (README,
  declared harnesses, no secrets); **one reviewer** checks only that it is
  not harmful.
- **Community → core**: the **maintainer's decision**, by MR, with no
  numeric threshold.

### Name and migration

- **Name**: Agentic Software Kit; package and command **`agentkit`**.
- **New repository** `agentic-software-kit`. First commit: the current tree
  squashed into a single `Legacy: ai-dev-toolkit 0.0.1 snapshot` commit,
  tagged `v0-legacy`. Then rebuilt towards **`v1.0.0`**, a deliberate
  breaking release. The old repository is archived after the switch.
- **Built on GitHub first** (no GitLab access from the current machine).
  `uvx --from git+<repo>@<tag>` and the CLI tests work there; the GitLab
  registry, `doctor --gitlab`, push rules and CI templates are written there
  but only validated after the move to the self-hosted GitLab.
- **Consumer projects** (a few, all the maintainer's): migrated by hand with
  `agentkit init --migrate`, which reads `.claude/.toolkit-sync-state`,
  deletes exactly the files the old sync wrote (its `files` list —
  hand-added files are not in it), **removes the keys the old sync merged
  into `.claude/settings.json`** (hooks, `attribution`,
  `includeCoAuthoredBy`, `enabledPlugins` entries, `companyAnnouncements`),
  moves competing tool configurations (see "Tool configurations"), then
  runs a normal `init`. Reviewed in an MR like any update. The user-scope
  side (`~/.claude/`, from `common-rules-user` etc.) is cleaned the same way
  by `agentkit user install --migrate`.
- **Build order**: (1) CLI skeleton — `catalog/`, `block.yaml`,
  `init` / `render` / `update` for core + one profile + one stack, managed
  `AGENTS.md` block, tests; (2) content, block by block, per the triage;
  (3) mechanics — lint configs, pre-commit, `doctor`, `docs`, `adr`;
  (4) GitLab — CI proposals, `doctor --gitlab`, registry publishing,
  `CATALOG.md`; (5) pilot on one real project with 2–3 harnesses;
  (6) tag `v1.0.0`, migrate the other projects.

### Handover

The successor is **not identified yet**: documentation and tests must stand
on their own for someone discovering the kit.

- **Documentation, two levels**: `README.md` (human, 5 minutes);
  `docs/maintaining.md` cut down to block anatomy, block lifecycle
  (community → core), release process, and a **"first contribution in 15
  minutes"** tutorial that doubles as a test of the docs; the kit's own
  `AGENTS.md` plus maintenance skills (`new-block`, `release`).
- **At v1, this file is split**: decisions → ~8–10 founding ADRs in
  `docs/adr/`; how it is built (block anatomy, ownership rule, commands,
  harness matrix) → `docs/architecture.md` and READMEs; `vision.md` keeps
  only the why, goals and roadmap (~60 lines).
- **Tests**: rendering snapshots (fixture project + `agentkit.yaml` →
  expected tree) and catalog lint (`block.yaml` schema, README present,
  `SKILL.md` frontmatter, always-loaded budget, `CATALOG.md` freshness, no
  secrets) in CI. **No scripted harness smoke test** (not every harness is
  available); the canary fixture and prompt are kept in `docs/` as a manual
  check when a harness ships a major version.
- **Releases on demand**, semver read from the consumer's side: major =
  the project must act (file moved, block removed, `agentkit.yaml` schema
  change); minor = new block or content; patch = fix. `CHANGELOG.md` filled
  in each MR; tag → CI publishes to the registry and creates the GitLab
  release; protected tags.
- **Governance enforced by GitLab**: `CODEOWNERS` (Premium) — `core/`,
  `profiles/`, `stacks/`, `src/` need a maintainer's approval;
  `community/` any reviewer.
- **Keep the kit small**: every block added is maintenance handed over.

## Code intelligence: measured

Benchmark run 2026-11-19 on three real repositories (CaliGrapHY Go/Wails,
FourmiFi Rust/Tauri, Commitment Go/Wails), six read-only navigation tasks
(call path, impact of a signature change, data flow) with a hand-checked
answer each, graded blind by an LLM judge. Headless Claude Code 2.1.327,
isolated from user settings, `.claude/` removed from the clones; each tool
got a one-paragraph "Code navigation" hint in `AGENTS.md`, as the kit would
ship it. 96 runs (4 configs × 6 tasks × Haiku/Sonnet × 2), after a 36-run
triage with Haiku.

| Model | Config | Correct | $/run | Turns | Tool used |
|---|---|---|---|---|---|
| Haiku | grep + Read | 92.6 % | 0.015 | 18.8 | — |
| Haiku | CodeGraph 1.6.2 | 93.3 % | 0.017 | 10.8 | 12/12 |
| Haiku | codebase-memory-mcp 0.12.1 | 95.8 % | 0.015 | 21.8 | 5/12 |
| Haiku | Serena 2.1.0 | 95.4 % | 0.016 | 24.4 | 10/12 |
| Sonnet | grep + Read | 97.2 % | 0.164 | 15.4 | — |
| Sonnet | CodeGraph | 95.8 % | 0.202 | 9.7 | 12/12 |
| Sonnet | codebase-memory-mcp | 95.8 % | 0.169 | 16.9 | 11/12 |
| Sonnet | Serena | 100 % | 0.166 | 18.3 | 10/12 |

What it settles:

- **grep + Read is enough for the core**, and a Haiku-class model is viable
  on it: the lever for cheaper runs is the model, not a tool.
- **No tool saves money.** CodeGraph cuts turns by ~40 % and wall time by
  ~15 % but costs more (its answers grow the context); the others cost the
  same as grep.
- **Accuracy gaps are 1–3 points**, within noise at n=12; Serena leads.
- **An installed tool is ignored without a hint** (triage: LSP and ast-grep
  0/6, Serena and codebase-memory 1/6), and a hint is no guarantee (Haiku
  loaded codebase-memory's tools and still used grep in 7 of 12 runs). A
  module that ships a tool ships its usage hint.
- Serena 2.1 exposes a single REPL tool by default; it needs
  `--agent-interface tools`. Its application code is GPL-3.0-or-later.
- Dropped: codebase-memory-mcp, ast-grep (no measured gain), Claude's LSP
  tool (not portable).

Not measured: editing tasks (refactors, renames — Serena's claimed
strength), other harnesses, repositories larger than ~250k lines.

## Open questions

1. **Harness spike** — done for the three CLIs (results above); the design
   holds, user level included. VS Code resolved by documentation (it hosts
   the Copilot and Claude harnesses; its Local harness is going away).
   Optional: run the canary fixture in VS Code's Copilot harness once someone
   has access.
2. ~~CodeGraph~~ — measured (see "Code intelligence: measured"). Decided:
   nothing in the core; CodeGraph and Serena as optional community modules.
   Re-run the benchmark at a major release of either, and add editing
   (refactor) tasks the first time someone proposes Serena for a project.
3. ~~"Outside a project" baseline~~ — decided: **opt-in** via
   `agentkit user install`, recommended at onboarding. Making it mandatory
   would have a project's `doctor` nag about a machine install that adds
   nothing inside an equipped project. Content: security + language (~1k
   chars), in a managed block of each harness's global instructions file.
4. ~~Migration~~ — decided (see "Name and migration"). Pilot: a Go/Wails
   tool.
5. ~~Handover~~ — decided (see "Handover").
6. **Embedded profile** — reserved; designed once the app profile has been
   proven on tools.
