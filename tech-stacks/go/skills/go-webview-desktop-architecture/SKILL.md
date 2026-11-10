---
name: go-webview-desktop-architecture
description: Choose, scaffold, and audit the architecture of a Wails 3 desktop app (Go + React). Use when building, structuring or reviewing one — where logic sits between the frontend and Go, splitting into packages or a multi-binary layout, services and the Services option, Taskfile build configuration, generated bindings, Go/JS events. Assumes Wails is already chosen; if no stack has been settled on, use desktop-app-architecture first.
---

# Wails Architecture

Pick an architecture profile for a Wails desktop app (Go backend, React frontend), scaffold it, or audit an existing one against it.

## Scope

**Wails 3 is the team's only supported version.** v3.0.0 has been stable since October 2026, with weekly feature releases since. Every project starts on it.

**Never write v2 patterns, even when memory suggests them.** The tell is `main.go`: v3 passes `Services:` to `application.New`, v2 passes `Bind:` to `wails.Run` (and has a `wails.json`). If a codebase turns out to be on v2, it is out of scope here: say so and ask the user how to proceed.

**Task stays the build system.** Upstream's Wake (`wails.yaml`, enabled with `WAILS_EXP_USE_WAKE=1`) and its purego backend are experimental, as are the Android and iOS targets, and all sit outside the stable compatibility contract. Don't adopt any of them by default; if a project wants one, it is that project's recorded decision.

If the user hasn't settled on Wails yet, defer to the `desktop-app-architecture` skill.

React is the mandated frontend for this stack. If the user wants a different frontend framework with Wails, the folder conventions here still mostly apply, but the React reference does not — say so rather than adapting it silently.

## Core idea

The folder tree is a **consequence**, not a decision. What determines a Wails project's shape is where business logic lives and what shape the Go↔JS boundary takes. A badly shaped boundary is not fixed by reorganizing folders, so settle the boundary before creating directories.

Two failure modes to guard against:

- **Over-structuring**: more packages, binaries or modules than there are consumers — a `core`/`domain`/`<capability>` package split, a `cmd/` or a `go.work` for a single frontend. This costs onboarding friction and buys nothing. The fixed layout below is not over-structuring: it is one frontend, one module, the same in every project.
- **Leaky boundary**: business logic scattered across React components and service methods, with no layer testable on its own. This is the expensive one, because fixing it means redesigning the boundary rather than moving files.

## The layout (the same for every profile)

Every Wails app of the portfolio has the same top-level shape, whatever its profile:

```text
my-app/
├── frontend/              # the React package, bindings/ generated inside it
├── build/                 # generated build assets and platform Taskfiles
├── internal/              # logic that does not need Wails (profiles B and C)
├── scripts/               # dev, check, build, package, release
├── <domain>service.go     # thin services, package main
├── main.go                # bootstrap only; embeds frontend/dist
├── Taskfile.yml           # APP_NAME, BIN_DIR
└── go.mod                 # one module; toolchain pinned, frontend/node_modules and build ignored
```

Why this and not Tauri's `apps/desktop/`: the layout follows the tool in both branches. Wails' generated tasks run `go build` at the root, and `main.go` embeds `frontend/dist` by relative path, so moving either costs an edit in every platform Taskfile, on every upgrade. What carries over is the point of having one layout: scripts, the gate and the docs are copied between projects unchanged, and adding a CLI later is an addition (`cmd/cli`), never a move.

One difference matters. Tauri's core crate has no Tauri dependency to reach for, so the compiler keeps Tauri out of `domain/`. In a single Go module, `internal/` only restricts who may import it, not what it imports. **The gate supplies the guarantee**: `references/check.ps1` fails when anything `internal/domain` depends on, directly or not, is Wails.

The profile decides **what goes where inside that layout**, not the top-level folders. Full trees are in `references/architecture.md` §3.

## Three Wails specifics to settle before the rest

- **Services are the boundary.** A service is an ordinary Go struct registered through `application.New(application.Options{Services: []application.Service{application.NewService(&MyService{})}})`. Its exported methods are what the frontend can call — nothing else is reachable. Unlike v2's bound structs, a service needs no Wails `context` in its signatures, which makes keeping business logic framework-free markedly easier than it used to be.
- **Typed bindings come with the toolchain.** `wails3 generate bindings` (run by the build tasks, so also by `wails3 dev`) produces TypeScript from the services' exported methods into `frontend/bindings/`, organized by package and service. Events registered with `application.RegisterEvent[T]("name")` are picked up too and get a typed JS/TS API. Shared types are therefore not a decision to make. The mistake to avoid is hand-writing TypeScript that duplicates generated output: it drifts, and the generated version wins at runtime.
- **There is no capabilities/permissions system.** Every exported method on a registered service runs with the full privileges of the Go process, and no manifest restricts what the frontend may reach. The practical substitute is discipline about what you register and what you export: **the set of services and their exported methods *is* the permission surface**, and it should be as narrow as the app actually needs. Say this explicitly rather than leaving it implicit — anyone arriving from a sandboxed stack will assume a restriction that does not exist here.

## The three profiles

Use the evocative names when talking to the user — they carry the intuition without requiring stack knowledge.

| Profile | Idea | Business logic | Use when |
|---|---|---|---|
| **A. The Storefront** | You look through it; nothing is made on site | React | UI over a remote API, little or no system access |
| **B. The Workshop** | Someone works at a bench with the machine's tools | React (workflows) + Go (system) | Files, Git, processes, local DB — **default choice** |
| **C. The Engine** | Self-contained mechanics that can power several vehicles | Go, in shared packages | A real second consumer exists (CLI, server, other frontend) |

Decision rules:

- **Default to B.** It absorbs early uncertainty best and is what most desktop apps actually need.
- **A** only when there's no meaningful system access.
- **C** only when a second consumer is real and identified. "We might need it later" is not a second consumer, and this is the most common over-structuring mistake.

**One caveat specific to v3 before reaching for C**: the toolchain already builds the same codebase as a GUI-less HTTP server (`wails3 task build:server`, `-tags server`), and it can target iOS and Android, experimentally. Neither of those is a second consumer in profile C's sense — they're the same application on another surface, built from the same root package, and neither justifies a multi-binary layout on its own. See §9 of the reference for what the server target does and does not solve.

**If that second consumer is a CLI companion to the desktop app, there are two ways to build it — never default, always ask which one fits:**

| | Single binary, dual-mode | Two separate binaries |
|---|---|---|
| What ships | One executable — runs as CLI with arguments, opens the window with none | Two executables |
| CLI weight | Carries the GUI framework compiled in, even when running as CLI | Lean — the CLI binary doesn't depend on Wails at all |
| Guarantee against GUI code leaking into CLI logic | None but discipline — same compilation unit | Enforced by the compiler — the CLI's `main` package has no Wails dependency, so it can't happen |
| Folder shape needed | None beyond profile B's — see `references/architecture.md` §3.B-CLI | Profile C's shape — see §3.C |
| Fits best | Simple distribution, no heavy scripted/looped use | CLI invoked repeatedly in scripts or CI, where startup weight matters |

This matters structurally, not just for naming: the single-binary option doesn't need profile C's shape at all — it stays inside profile B with one added file.

A note on scope: a local HTTP sidecar (a Go process exposing HTTP instead of service bindings) is occasionally seen in the wild, but it's rare enough, and different enough in its concerns (port management, process lifecycle), that it isn't documented here as a profile. If the user's project genuinely needs one, treat it as a one-off design problem rather than reaching for a template.

## The six decisions

Settle these before creating folders. Full detail is in `references/architecture.md` (§4).

| # | Decision | Default answer |
|---|---|---|
| W1 | Where does business logic live? | Follows the profile |
| W2 | Shape of the service surface | Thin service methods, use-case oriented, minimal exported surface (see security note above) |
| W3 | Go-side state | Stateless; struct fields with `sync.Mutex`/`RWMutex` if shared across goroutines; one owning goroutine beyond 2–3 mutexes |
| W4 | Error boundary | One typed error (`*AppError` with a stable `Code`) returned as `error`, read from `error.cause` in `ipc/client.ts`; never an internal error passed through |
| W5 | Long-running work | Beyond ~500 ms: registered typed events (`application.RegisterEvent[T]`, `app.Event.Emit`), and `context.Context` first so the frontend can cancel |
| W6 | Frontend location | `frontend/` — the Wails default, already a subfolder, no configuration cost |

W2 is the structuring one — spend the effort there. The other five follow from it or from the profile.

## Workflow: scaffolding a new project

1. **Determine the profile.** Ask about: what the app does, expected system access, team size, and whether a second consumer of the business logic is planned. Don't assume.
2. **Propose before building.** State the recommended profile and W1–W6 values, get agreement.
3. **Read `references/architecture.md`** (§3 for the tree, §5 for scaffolding rules) and **`references/react-conventions.md`** for the frontend side — it defines the `ipc/` / `bindings/` split, the server-state layer, the error handling layers, and the state management default.
4. **Scaffold with `wails3 init -n <name> -t react -mod <module path>`** rather than writing the tree by hand, then move the generated service into the shape §3 describes. The generated `build/` tree and Taskfiles are load-bearing — don't reconstruct them from memory. Pass the real module path now (§5, rule 2).
5. **Create only what is used.** No empty folders, no placeholders for unjustified layers.
6. **Keep service methods thin.** A service method should: receive the call, invoke `internal/domain`, map the error into the typed result, return. If a service method's body is doing real logic rather than delegating, the boundary has already leaked — and so has the mirror-image mistake of one method per domain function, which turns the service surface into a copy of the domain API instead of a use-case one.
7. **Design the error type early.** One `Code`+`Message` error type, returned as `error` by every service method (§4, W4) — retrofitting this after several methods return internal errors is expensive.
8. **Be deliberate about the exported surface.** Since there's no capability sandbox, review what's registered and what's exported as if it were the permission boundary — because it is one, in practice.
9. **Set up the fixed pieces** (§5): the pinned toolchain and the two `ignore` lines in `go.mod`, the script names with `references/check.ps1` as `scripts/check.ps1`, one dev port per app, and `go-code-standards` for the lint configuration.
10. **Generate nothing tied to a forge or CI system.** No `.github/`, no `.gitlab-ci.yml`, no pipeline files, unless the user explicitly asks.
11. **Document W1–W6 in the project README.**

## Workflow: auditing an existing project

1. **Confirm it's a v3 codebase** (`Services:` in `main.go`, `frontend/bindings/`, a `Taskfile.yml`). If it's v2, stop and tell the user: this reference doesn't apply. Check that the three Wails versions agree (§5).
2. **Read `references/architecture.md`** (§6 anti-patterns, §4 decisions) and `references/react-conventions.md` (§8 shared frontend anti-patterns).
3. **Identify the actual profile** and the gap with the appropriate one. A project with a `cmd/cli` nobody uses is really a Workshop carrying an extra binary. A project off the common layout is a finding too, ranked low.
4. **Walk the anti-pattern checklist**, present/absent/not applicable, with file and line as evidence. An audit without file references can't be acted on.
5. **Check the service surface specifically**: is every exported method on a registered service something the app genuinely needs exposed, or is a broad service registered "for convenience"? This is easy to miss because there is no manifest file to review — the permission surface has to be read from the `Services:` list and the methods' capitalization.
6. **Assess W1–W6 as actually implemented.**
7. **Rank findings by increasing cost to fix**, so the user can start with what's cheap.
8. **Modify no files** unless asked. An audit that silently rewrites code can't be trusted or reviewed.

Priority when reporting: leaky boundaries (anti-patterns 1, 2, 3, 9) and the exposed surface (5, 19) matter more than naming or layout issues, because they are the ones that compound.

## Workflow: migration and refactoring

One misconception to correct up front: **there is no easy migration from B to C.** What changes is the shape of the boundary, not where code sits — moving files without redesigning the boundary produces profile C's cost with profile B's coupling.

1. **Check the prerequisite**: is `internal/domain` free of any Wails import? v3 no longer forces a `context` on service methods, so this is usually cleaner than it was in v2 — but check for event emission and application/window calls reaching down into domain code.
2. **Describe the target boundary before moving code** — service methods, payloads, error types, event contracts.
3. **Extract module by module**, never wholesale.
4. **Justify each new package**: size, boundary stability, and consumers.
5. For a targeted fix, change **only** the anti-pattern named, and explain the change before applying it.

## Workflow: evolving toward a server with remote clients

Three points need surfacing, because none are covered by W1–W6 and all three are easy to get wrong:

1. **Not everything in `internal/domain` can centralize** — local file/process access stays client-side; classify module by module. This is a product decision, not a mechanical refactor.
2. **Design W2 as if it were already a network API** — use-case-oriented service methods reuse cleanly as HTTP handlers later (Go makes this concretely easy: a service method and an HTTP handler can share the same underlying `internal/domain` call with very little adaptation).
3. **Multi-user auth and data isolation are unaddressed by anything here** — and this is *more* pressing in v3, not less, because `wails3 task build:server` will hand you a running HTTP server from the same code in one command. That build serves one application to whoever reaches it; it grants no notion of users, sessions, or isolation between them. Treat that as a separate design pass, and say so before anyone mistakes the server target for a multi-client architecture.

## Reference files

- `references/architecture.md` — §1 decisions, §2 profile selection, §3 folder trees per profile, §4 cross-cutting decisions in detail, §4b runtime data and log locations, §5 scaffolding rules, §6 the anti-pattern checklist, §7 evolution path, §8 standalone prompts, §9 evolving toward a server with remote clients.
- `references/check.ps1` — the gate, copied to `scripts/check.ps1`.
- `references/nsis/project.nsi` — ready-made per-user installer script (update in place, safe uninstall, French/English, desktop shortcut); `references/nsis/path.nsh`, `references/nsis/upgrade.nsh` — its NSIS includes: optional user `PATH` entry, update in place (architecture.md §5, item 18); `references/nsis/install-nsis.md` — installing `makensis` from the NSIS zip, without admin rights.
- `references/react-conventions.md` — frontend conventions for the React side: folder shape, server state, error handling layers, state management default, testing approach.
- The front end's tooling (Prettier, ESLint, `tsc`, Vitest) is the `frontend-code-standards` skill of the `tech-stack-web-frontend` block, offered on any Wails project; the Go tooling is `go-code-standards`; for hands-on user testing of the running app, `frontend-feedback`, from the same block.

For scaffolding, architecture.md §3/§5 plus the React reference are usually enough. For an audit, §6/§4 plus the React reference's §8.
