# ai-dev-toolkit

A shared Claude Code configuration for a multi-stack engineering team:
security/git rules, a project-type discipline, and per-language architecture
guidance — authored once here, pulled into each project on purpose.

## How it's deployed and maintained

**Synced and committed, not installed.** Run the sync command once
against a project — it writes rules/skills/hooks into that project's own
`.claude/`, you review the diff, and you commit it like any other
change. From that point on it's just files in the repo: any teammate who
`git pull`s the project gets them automatically, nothing to install or
run on their side.

**Nothing runs automatically.** No session-start check, no proactive
prompt. Run `/toolkit-sync` whenever you want to know whether a project
is missing something or has drifted from what's currently expected — it's
read-only, and if there's anything to apply it prints the exact command
for you to run yourself.

**Why not an internal plugin marketplace.** Claude Code supports
installing plugins from a marketplace — one command, auto-updating,
nothing to read. We deliberately don't distribute this way. The team is
still learning to work with an agent, and a rule file you can open,
question, and edit teaches that; a plugin install does not. Sync-and-
commit costs a bit more (pulling an update is a deliberate command, not
automatic) in exchange for every convention being visible, readable, and
owned by the project it's in.

## Deploying

Once per machine, in Git Bash / macOS / Linux:

```
curl -fsSL https://raw.githubusercontent.com/thomasdevaux/ai-dev-toolkit/main/install.sh | bash
```

or in PowerShell:

```
irm https://raw.githubusercontent.com/thomasdevaux/ai-dev-toolkit/main/install.ps1 | iex
```

It clones this repo into `~/.cache/ai-dev-toolkit` (or updates it if
already there — the same cache path `/toolkit-sync` reuses afterwards, so
there's only ever one checkout on disk) and syncs the user-scope baseline
into `~/.claude/`. From then on, run `/toolkit-sync` inside any project's
git repository to see what's missing (the common rules, and a
project-type profile — pick `project-type-none` / `project-type-app` /
`project-type-embedded-fccu`) and get the command to sync it yourself.
Commit what it writes. Re-run the install command, or `/toolkit-sync`,
later to pull in toolkit updates.

**No Claude Code session? Same check, plain script.** `/toolkit-sync` and
`/toolkit-help` are thin wrappers around `toolkit-status` and `toolkit-help`
— two scripts sitting at the root of the cloned checkout, runnable from any
terminal (a CI job, a git hook, or just a shell) without ever opening Claude
Code:

```
~/.cache/ai-dev-toolkit/toolkit-status --project-dir /path/to/project
~/.cache/ai-dev-toolkit/toolkit-help
```

(`.cmd` counterparts for cmd/PowerShell.) Same report, same handbook text —
just no agent paraphrasing it for you.

## What it covers

Two deployment scopes, synced independently — a project's `.claude/`
(committed, reviewed, per repo) and your machine's `~/.claude/`
(installed once, applies to every folder including scratch ones).

| Block | Feature | Scope | Tier | Type | What it does |
|---|---|---|---|---|---|
| common-rules | `security` | project / user | baseline | rule | Never commit secrets; rotate and report immediately if one leaks; review third-party dependencies before merging. |
|  | `language` | project / user | baseline | rule | Code, comments and commits in English; conversational replies in the user's language. |
|  | `project-type-profile` | project / user | baseline | rule | Enforces picking exactly one project-type profile (see below) and checking it before non-trivial work. |
|  | `codegraph` | project / user | baseline | rule | Prefer the local code graph over grep for symbol-level questions, when one is indexed. |
|  | `caveman` | project / user | baseline | skill | Opt-in ultra-compressed replies — measured ~65% fewer output tokens. |
|  | `codegraph-setup` | project / user | baseline | skill | Install, first-index, verify, or remove the local code graph. |
|  | `codegraph-reindex` | project / user | baseline | agent | Re-indexes a stale code graph, on a cheaper model — the one CodeGraph operation that needs no judgment. |
|  | `session-report` | project / user | baseline | skill | Builds an HTML usage report (tokens, cache, cost, anomalies) from local session transcripts. |
|  | `commit-message-format` | project / user | baseline | skill | Commit subject/body conventions, applied when writing a commit. The ban on AI-attribution trailers it states is also enforced by `includeCoAuthoredBy: false` in the same block's `settings_patch`, so it holds whether or not the skill is invoked. |
|  | `desktop-app-architecture` | project / user | baseline | skill | Picks a stack for a new desktop app or internal tool, then hands off to the matching tech-stack block; also audits whether an existing choice still fits. |
|  | `codegraph-freshness` | project / user | baseline | hook | At session start: warns when the code graph's index is behind the code, and — on a repo past 300 indexable sources with no index — offers to install it. Silent otherwise. |
|  | `style-save` | user | baseline | hook | Persists the active caveman intensity to the statusline whenever the skill is invoked (manually or auto-triggered) — no session-start question. |
| context-quality | `project-context` | project | baseline | rule | Fixes `AGENTS.md` to one skeleton; `CLAUDE.md` becomes a one-line `@AGENTS.md` pointer to it. |
|  | `init-project-context` | project | baseline | skill | Bootstraps `AGENTS.md` from what the repository actually contains. |
|  | `audit-project-context` | project | baseline | skill | Reviews `AGENTS.md` for accuracy, size, and skeleton conformance; `session` mode instead harvests what a session learned. |
|  | `context-check` | project | baseline | hook | Flags a missing, oversized, or stale `AGENTS.md` at session start. |
| toolkit-self-check | `/toolkit-sync` | project / user | baseline | command | On-demand, read-only onboarding/drift check against the manifest; prints the exact command to sync yourself. |
|  | `/toolkit-feat` | project / user | baseline | command | Lists suggested-tier blocks and detected tech stacks not yet synced. |
|  | `/toolkit-help` | project / user | baseline | command | Points at the handbook and README on GitHub. |
| gitlab | `gitlab` | project | suggested | plugin | Merge requests, issues, and pipelines from inside the session. Opt-in — sync it by id if the project actually uses GitLab. |
| project-type-none | `no-project-type` | project | choice-group: project-type | rule | No docs, requirements, or ADRs imposed — the common rules still apply, and switching to `project-type-app` is one `sync switch` away. |
| project-type-app | `docs-map` | project | choice-group: project-type | rule | Ten fixed documentation slots; content that fits none is flagged to the user, never filed ad hoc. |
|  | `requirements` | project | choice-group: project-type | rule | `docs/requirements.md` is one `##` section per requirement: id, status, free-form prose. |
|  | `adr` | project | choice-group: project-type | rule | `docs/adr/` — what deserves an ADR, what binds, and what to do when a request conflicts with an accepted one. |
|  | `testing-strategy` | project | choice-group: project-type | rule | Non-trivial features need at least one automated test of the main path; no numeric coverage threshold. |
|  | `init-project-docs` | project | choice-group: project-type | skill | Scaffolds the `docs/` tree: the filled slots and the on-hold stubs. |
|  | `audit-docs` | project | choice-group: project-type | skill | Checks docs against the doc map: missing slots, stale content, requirements consistency. |
|  | `adr-cleanup` | project | choice-group: project-type | skill | Gardens `docs/adr/` — flags contradictions, proposes consolidations, regenerates `INDEX.md`. |
|  | `write-adr` | project | choice-group: project-type | skill | Writes one: numbering, the Nygard format, the `INDEX.md` row, and supersede chains. |
|  | `docs-lint` | project | choice-group: project-type | agent | The mechanical half of `audit-docs` and `adr-cleanup`, on a cheaper model: doc-map slot presence, requirements-table validity, ADR status vocabulary, `INDEX.md` drift. Reports findings, judges nothing. |
|  | `improve-architecture` | project | choice-group: project-type | skill | Ranks structural friction as deepening candidates in a self-contained HTML report, then grills the chosen one before any code moves. |
|  | `git-workflow-app` | project | choice-group: project-type | rule | The two prohibitions only: no commit on `main`/`master`/`develop` outside the merge step, no push or PR without explicit acceptance. |
|  | `git-workflow-app` | project | choice-group: project-type | skill | The procedure: six branch types (`feat` `fix` `test` `docs` `chore` `sandbox`), agent proposes the name, squash-then-rebase, PR-or-`--no-ff`-merge, branch deleted local and remote. |
|  | `git-branch-guard` | project | choice-group: project-type | hook | Denies a `git commit` issued on `main`/`master`/`develop` — the one half of the workflow a script can decide without judgment. Silent everywhere else, including a merge commit closing a conflict. |
| project-type-embedded-fccu | `embedded-fccu-project-type-stub` | project | choice-group: project-type | rule | Stub for embedded/safety-critical software (e.g. a fuel cell control unit) — not designed yet; points to `project-type-app`'s rules in the toolkit checkout since its own files aren't synced alongside it. |
| tech-stack-python | `python-desktop-architecture` | project | tech-stack | skill | PySide6/tkinter structure, packaging, protecting sensitive logic. Detected from `pyproject.toml`, `requirements.txt`, `setup.py`. |
|  | `style` (Python) | project | tech-stack | rule | Scoped to `**/*.py`: run ruff and mypy, silence a finding only with a named rule and a reason, annotate what crosses a module boundary. |
|  | `python-code-standards` | project | tech-stack | skill | Installs the shared ruff + mypy configuration, diffs an existing one against it, and sequences adoption on a codebase with a backlog. |
| tech-stack-rust | `rust-webview-desktop-architecture` | project | tech-stack | skill | Tauri 2 architecture (React + Vite + Rust webview). Detected from `Cargo.toml`. |
|  | `style` (Rust) | project | tech-stack | rule | Scoped to `**/*.rs`: `Result` over panic, narrowest visibility, `// SAFETY:` on every `unsafe`, allow a lint only with a reason. |
|  | `rust-code-standards` | project | tech-stack | skill | Installs the shared `[lints]` table and `rustfmt.toml`, diffs an existing one against it, and sequences clippy adoption. |
| tech-stack-go | `go-webview-desktop-architecture` | project | tech-stack | skill | Wails 3 architecture (Go + React webview). Detected from `go.mod`. |
|  | `style` (Go) | project | tech-stack | rule | Scoped to `**/*.go`: wrap errors with `%w`, `context.Context` first and never stored, every goroutine has a stated exit. |
|  | `go-code-standards` | project | tech-stack | skill | Installs the shared `.golangci.yml` (v2 schema, gofumpt), migrates a v1 config, and sequences adoption on a module with a backlog. |
| tech-stack-dotnet | `dotnet-desktop-architecture` | project | tech-stack | skill | Avalonia/MVVM structure, Native AOT publishing. Detected from `*.csproj`, `*.sln`. |
|  | `style` (C#) | project | tech-stack | rule | Scoped to `**/*.cs`: warnings are build errors, nullable stays on, async all the way down, suppress only with a rule id and a reason. |
|  | `dotnet-code-standards` | project | tech-stack | skill | Installs the shared `Directory.Build.props` and `.editorconfig` severities, and sequences nullable adoption project by project. |
| tech-stack-frontend-design | `frontend-design` | project | tech-stack | plugin | Official frontend-design plugin - UI/component design guidance for web frontends. Detected from `package.json`. |
| user-statusline | `statusline` | user | baseline | tool | Status line showing model, context usage, and rate limits — the one always-on token-budget feedback. |
| language-servers | 13 official servers | user | baseline | plugin | Go-to-definition and diagnostics, one per language: `pyright` / `typescript` / `rust-analyzer` / `gopls` / `csharp` / `clangd` / `jdtls` / `kotlin` / `swift` / `ruby` / `php` / `lua` / `liquid`. |
| skill-creator | `skill-creator-user` | user | suggested | plugin | Official skill-creator plugin — writes, benchmarks and tunes the triggering of an Agent Skill. Opt-in, per machine (`--user`), for when you're about to author one. Its output is a plain `.claude/skills/` that sync does not track, and its eval loop spawns several full Claude sessions per iteration. |

Want the detail behind a specific rule or skill? Read the file itself —
every block that lands in a project's `.claude/` is meant to be opened
and read, not paraphrased elsewhere.

## Documentation

[`handbook/`](handbook/) — how the team is meant to work with an agent
day to day. Written for people, not about the toolkit.
