# User guide: adopting this toolkit in your project

For teams syncing this toolkit's conventions into their own project. See
[`vision.md`](vision.md) for why this exists, [`architecture.md`](architecture.md)
for how it works internally, and [`../handbook/`](../handbook/) for how to work
with an agent day to day — a different corpus, written for people rather than
about the toolkit.

## Quickstart

### Once per machine

```
python -m tools.sync sync --user --toolkit-root .
```

This installs every user-scope baseline entry in `~/.claude/`: the common
block (rules, `caveman`, `codegraph-setup`), the status line, the drift check,
and the 13 official language servers.

It's the step that makes **opening a session anywhere** worth it. A scratch
folder gets the rules, the language servers and the status line without a
single project file being created, and the drift check stays quiet there.

It also covers every project on the machine — `~/.claude/` applies everywhere —
which is why the language servers live at user scope and not in each project's
baseline. The trade-off: a teammate who skips this step doesn't get them, since
nothing about it is committed to the project repo.

Pass explicit ids to pick one by one (`common-rules-user`, `user-statusline`,
`pyright-lsp-user`, …).

### Per project, in a git repository

```
# what's suggested here
python -m tools.sync detect --project-dir /path/to/your/project

# every tier:baseline entry at once
python -m tools.sync sync --toolkit-root . --project-dir /path/to/your/project

# exactly one process profile
python -m tools.sync sync process-light --toolkit-root . --project-dir /path/to/your/project

# whatever detect suggested
python -m tools.sync sync tech-stack-python --toolkit-root . --project-dir /path/to/your/project
```

Each `sync` call prints the files it would create or change (and any
`settings.json` key it would patch) and asks for confirmation before writing
anything. Review the diff, commit the result like any other change. Re-running
later is idempotent.

Running `sync` with no entry ids syncs every `tier: baseline` entry for that
scope at once, so new baseline entries are picked up without updating this
guide. Anything that isn't baseline always requires an explicit id — that's
the point of the tiers.

### Then set up the project's context

```
# in a session on the project
> use the init-project-context skill      # AGENTS.md + the CLAUDE.md pointer
> use the init-project-docs skill         # the docs/ tree (process-light only)
```

## Block catalog

| Manifest id(s) | Tier | Scope | What it is |
| --- | --- | --- | --- |
| `common-rules` | baseline | project | Rules (security, git workflow, language, process profile, code navigation) plus two always-available skills: `caveman` for output compression, `codegraph-setup` for the code graph. |
| `common-rules-user` | baseline | user | The same block in `~/.claude/`, so any folder has it. |
| `context-quality` | baseline | project | `AGENTS.md` as the single context file: fixed skeleton, init and audit skills, `revise-agents-md` command, session-start check. |
| `gitlab` | baseline | project | Official GitLab plugin. |
| `process-none` / `process-light` / `process-full` | choice-group:process | project | Pick exactly one. See below. |
| `tech-stack-python` | tech-stack (`pyproject.toml`, `requirements.txt`, `setup.py`) | project | Python desktop architecture — PySide6/tkinter, packaging, protecting sensitive logic. |
| `tech-stack-rust` | tech-stack (`Cargo.toml`) | project | Rust + Tauri desktop architecture. |
| `tech-stack-go` | tech-stack (`go.mod`) | project | Go + Wails desktop architecture. |
| `tech-stack-dotnet` | tech-stack (`*.csproj`, `*.sln`) | project | .NET + Avalonia desktop architecture. |
| `user-statusline` | baseline | user | Model, context usage and rate limits in the prompt. See [`statusline.md`](statusline.md). |
| `<lang>-lsp-user` ×13 | baseline | user | Official language servers: pyright, typescript, rust-analyzer, gopls, csharp, clangd, jdtls, kotlin, swift, ruby, php, lua, liquid. |
| `toolkit-self-check` / `toolkit-self-check-user` | baseline / baseline | project / user | Session-start drift report. |

Every id is a literal `sync-manifest.yaml` entry, and each carries a
`summary:` there — that field is the source for this table. `detect` only ever
*suggests*; nothing syncs without an explicit command.

**What isn't here:** blocks written but not yet validated on a real project
live in [`../incubator/`](../incubator/) and cannot be synced — embedded C,
model-based design, Node.js, and the per-language style/packaging rules. See
that directory's README for how one gets promoted.

## The four tiers, from the user's side

- **baseline** — expected on every project; the drift report lists it as
  missing until you sync it.
- **choice-group** — exactly one member, enforced at sync time.
- **tech-stack** — suggested from marker files, never automatic.
- **suggested** — listed once as "available, not installed", then never
  pressed again.
- **optional** — never surfaced at all; you sync it by id because you already
  know you want it.

## Process profile: none, light, full

A [choice-group](architecture.md#mutual-exclusion): every project syncs
**exactly one**. `tools/sync` refuses the second while the first is
registered.

- **`process-none`** — scripts, one-offs, tinkering. No docs tree, no
  requirements, no decisions log. The common rules still apply.
- **`process-light`** — the default for an application or tool with its own
  repository. Brings the **doc map** (ten slots, five filled at init and five
  as stubs carrying their own trigger), the requirements table, the decisions
  log, the testing policy, `audit-docs`, and the `desktop-app-architecture`
  skill for choosing a stack.
- **`process-full`** — critical or certified software. **Still a stub**: it
  tells Claude to follow `process-light` until its extra rigor is designed.

If none is synced, `common/rules/process-profile.md` has Claude ask before
non-trivial work — but only in a git repository. A scratch folder is never
asked anything.

## Choosing a stack for a new desktop app

`process-light` carries `desktop-app-architecture`, which picks between the
Python, web-based (Rust/Go) and .NET branches. It deliberately lives there
rather than in a stack block: the choice happens *before* `pyproject.toml` or
`Cargo.toml` exists, when stack detection has nothing to detect.

Once the branch is chosen it hands off — it names the block to sync and gives
the command, and the specialized skill takes over from there:

```
python -m tools.sync sync tech-stack-rust --toolkit-root <checkout> --project-dir .
```

## Automatic drift checks (toolkit-self-check)

A `SessionStart` hook reports, at the start of every session, whether the
project is missing baseline/choice-group entries or has drifted from what's
synced. It resolves its own toolkit copy: `AI_DEV_TOOLKIT_ROOT` if set,
otherwise a cache at `~/.cache/ai-dev-toolkit` (pulled at most hourly).

**It stays quiet where it should.** A folder that is neither a git repository
nor previously synced gets a single line, not an onboarding checklist — see
[`decisions.md`](decisions.md#d-09) for why.

Every project gets the check once it syncs the baseline. The user-scope entry
covers the case a project hook can't: a brand-new, never-synced project.

The report is read-only. The deployed hook is a thin stub that resolves the
checkout and hands off to that checkout's own
`tools/hooks/toolkit-drift-check-impl.sh`, so fixes there reach every project
on the next throttled pull — no re-sync needed.

## Official plugins

Only one remains a dependency: `gitlab`. The toolkit previously also depended
on `claude-md-management`; its criteria now live in `context-quality`'s own
skills and the dependency is gone — see [`decisions.md`](decisions.md#d-06)
and [`../handbook/plugins-policy.md`](../handbook/plugins-policy.md) for when
we depend, copy, or write our own.

**The 13 language servers are user-scope baseline**, installed by the
per-machine command rather than per project. Their measured context cost is
zero — no skill, command or agent, they only wire up a language server — so
there's nothing to gain by picking them one language at a time, and a scratch
session gets them too.

An `official-plugin` entry writes **no files** — it has no `source`. It adds
one key to `settings.json`:

```json
"enabledPlugins": { "pyright-lsp@claude-plugins-official": true }
```

What isn't measured: what a language server does when its binary isn't
installed on the machine. If one turns out to be noisy rather than inert, drop
that entry — see [`decisions.md`](decisions.md#d-12).

You can always install an official plugin directly (`/plugin install
<name>@claude-plugins-official`) without this toolkit — syncing an
`official-plugin` entry just patches `enabledPlugins` for you.

**Pruning:** every `sync` run checks the target `settings.json` for
`enabledPlugins` entries no manifest entry references anymore, and offers to
remove each one. That's how a dropped dependency (like
`claude-md-management`) leaves a project cleanly.

## Language

Code, comments, commit messages and documentation are written in English —
in this repo and in any project syncing `common-rules`. Conversation with
Claude happens in whatever language you write in. See
`common/rules/language.md`.

## Pointing a project back at this toolkit

Once a project has synced from this repo, its `AGENTS.md` should say so:

```markdown
## Toolkit conventions
Conventions come from `ai-dev-toolkit` (<repo-url>), ref
`<git-sha-or-tag>`. `.claude/.toolkit-sync-state` lists exactly which
blocks and files are toolkit-managed.
```

The state file is the source of truth for what's synced.
