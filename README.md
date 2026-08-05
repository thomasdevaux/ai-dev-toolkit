# ai-dev-toolkit

A shared Claude Code configuration for a multi-stack engineering team:
security/git rules, a process discipline, and per-language architecture
guidance — authored once here, pulled into each project on purpose.

## How it's deployed and maintained

**Synced and committed, not installed.** Run the sync command once
against a project — it writes rules/skills/hooks into that project's own
`.claude/`, you review the diff, and you commit it like any other
change. From that point on it's just files in the repo: any teammate who
`git pull`s the project gets them automatically, nothing to install or
run on their side.

**Every session checks itself.** Each time Claude Code opens in a synced
project (or in a fresh one), a session-start hook compares what's synced
against what's currently expected and tells you — at the start of the
conversation — if anything is missing or out of date, offering to sync
it. Nothing is ever written without your confirmation; the check only
ever *offers*, it never writes on its own.

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

That's the only command you need to run by hand — pick whichever shell
you have open. It clones this repo into `~/.cache/ai-dev-toolkit` (or
updates it if already there — the same cache path the session-start
check reuses afterwards, so there's only ever one checkout on disk) and
installs the check itself. From then on, opening a Claude Code session
inside any project's git repository is enough: the check tells you
what's missing (the common rules, and a process profile — pick
`process-none` / `process-light` / `process-full`), and syncs it for you
once you confirm. Commit what it writes. Re-run the install command
later, or answer yes the next time a session flags a newer version
pending, to pull in toolkit updates.

## What it covers

Two deployment scopes, synced independently — a project's `.claude/`
(committed, reviewed, per repo) and your machine's `~/.claude/`
(installed once, applies to every folder including scratch ones).

| Block | Feature | Scope | Tier | Type | What it does |
|---|---|---|---|---|---|
| common-rules | `security` | project / user | baseline | rule | Never commit secrets; rotate and report immediately if one leaks; review third-party dependencies before merging. |
| common-rules | `language` | project / user | baseline | rule | Code, comments and commits in English; conversational replies in the user's language. |
| common-rules | `process-profile` | project / user | baseline | rule | Enforces picking exactly one process profile (see below) and checking it before non-trivial work. |
| common-rules | `codegraph` | project / user | baseline | rule | Prefer the local code graph over grep for symbol-level questions, when one is indexed. |
| common-rules | `caveman` | project / user | baseline | skill | Opt-in ultra-compressed replies — measured ~65% fewer output tokens. |
| common-rules | `codegraph-setup` | project / user | baseline | skill | Install, index, refresh, or remove the local code graph. |
| common-rules | `desktop-app-architecture` | project / user | baseline | skill | Helps pick a stack for a new desktop app. |
| context-quality | `project-context` | project | baseline | rule | Fixes `AGENTS.md` to one skeleton; `CLAUDE.md` becomes a one-line `@AGENTS.md` pointer to it. |
| context-quality | `init-project-context` | project | baseline | skill | Bootstraps `AGENTS.md` from what the repository actually contains. |
| context-quality | `audit-project-context` | project | baseline | skill | Reviews `AGENTS.md` for accuracy, size, and skeleton conformance. |
| context-quality | `context-check` | project | baseline | hook | Flags a missing or stale `AGENTS.md` at session start. |
| toolkit-self-check | `toolkit-drift-check` | project / user | baseline | hook | Reports this project's onboarding/drift status against the manifest at session start — the message you see when a sync is pending. |
| gitlab | `gitlab` | project | baseline | plugin | Merge requests, issues, and pipelines from inside the session. |
| process-none | `no-process` | project | choice-group: process | rule | No docs, requirements, or ADRs imposed — common rules still apply. |
| process-light | `docs-map` | project | choice-group: process | rule | Ten fixed documentation slots; content that fits none is flagged to the user, never filed ad hoc. |
| process-light | `requirements` | project | choice-group: process | rule | `docs/requirements.md` is one status table: id, one-line requirement, status. |
| process-light | `adr` | project | choice-group: process | rule | `docs/adr/` — one Nygard-format file per decision, active/archive split, a generated `INDEX.md`. |
| process-light | `testing-strategy` | project | choice-group: process | rule | Non-trivial features need at least one automated test of the main path; no numeric coverage threshold. |
| process-light | `init-project-docs` | project | choice-group: process | skill | Scaffolds the `docs/` tree: the filled slots and the on-hold stubs. |
| process-light | `audit-docs` | project | choice-group: process | skill | Checks docs against the doc map: missing slots, stale content, requirements consistency. |
| process-light | `adr-cleanup` | project | choice-group: process | skill | Gardens `docs/adr/` — flags contradictions, proposes consolidations, regenerates `INDEX.md`. |
| process-light | `git-workflow-light` | project | choice-group: process | rule | Branch per feature, rebase before merge, squash commits, PR-or-local-merge, no AI-attribution trailers. |
| process-light | `commit-message-format` | project | choice-group: process | skill | Structured commit-message subject/body conventions, applied when writing a commit. |
| process-full | `full-process-stub` | project | choice-group: process | rule | Stub for critical/certified software — follows `process-light`'s rules until designed. |
| tech-stack-python | `python-desktop-architecture` | project | tech-stack | skill | PySide6/tkinter structure, packaging, protecting sensitive logic. Detected from `pyproject.toml`, `requirements.txt`, `setup.py`. |
| tech-stack-rust | `rust-webview-desktop-architecture` | project | tech-stack | skill | Tauri 2 architecture (React + Vite + Rust webview). Detected from `Cargo.toml`. |
| tech-stack-go | `go-webview-desktop-architecture` | project | tech-stack | skill | Wails architecture (Go + React webview). Detected from `go.mod`. |
| tech-stack-dotnet | `dotnet-desktop-architecture` | project | tech-stack | skill | Avalonia/MVVM structure, Native AOT publishing. Detected from `*.csproj`, `*.sln`. |
| user-statusline | `statusline` | user | baseline | tool | Status line showing model, context usage, and rate limits — the one always-on token-budget feedback. |
| language-servers | 13 official servers | user | baseline | plugin | Go-to-definition and diagnostics, one per language: `pyright` / `typescript` / `rust-analyzer` / `gopls` / `csharp` / `clangd` / `jdtls` / `kotlin` / `swift` / `ruby` / `php` / `lua` / `liquid`. |

Want the detail behind a specific rule or skill? Read the file itself —
every block that lands in a project's `.claude/` is meant to be opened
and read, not paraphrased elsewhere.

## Documentation

[`handbook/`](handbook/) — how the team is meant to work with an agent
day to day. Written for people, not about the toolkit.
