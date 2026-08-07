---
name: go-webview-desktop-architecture
description: Choose, scaffold, and audit the architecture of a Wails 3 desktop app (Go + React). Use when building, structuring or reviewing one — where logic sits between the frontend and Go, splitting into packages or a multi-binary layout, services and the Services option, Taskfile build configuration, generated bindings, Go/JS events. Assumes Wails is already chosen; if no stack has been settled on, use desktop-app-architecture first.
---

# Wails Architecture

Pick an architecture profile for a Wails desktop app (Go backend, React frontend), scaffold it, or audit an existing one against it.

## Scope

This skill covers **Wails 3** and nothing else. v3 is in beta with a stable desktop API and production apps shipping on it; v2 is still upstream's stable release but is not covered here — new projects start on v3, so that a project doesn't land on the older architecture the month before it would have had to migrate anyway. Upstream publishes a v2→v3 migration guide and reports 1–4 h for a typical app.

**Check which version a codebase uses before writing anything, and don't guess from phrasing.** The tell is `main.go`: v3 passes `Services:` to `application.New`, v2 passes `Bind:` to `wails.Run`. On a v2 codebase, say plainly that this skill doesn't cover it and point at the upstream migration guide rather than translating v2 patterns on the fly.

If the user hasn't settled on Wails yet, defer to the `desktop-app-architecture` skill.

React is the mandated frontend for this stack. If the user wants a different frontend framework with Wails, the folder conventions here still mostly apply, but the React reference does not — say so rather than adapting it silently.

## Core idea

The folder tree is a **consequence**, not a decision. What determines a Wails project's shape is where business logic lives and what shape the Go↔JS boundary takes. A badly shaped boundary is not fixed by reorganizing folders, so settle the boundary before creating directories.

Two failure modes to guard against:

- **Over-structuring**: multiple Go packages, a multi-binary layout, or premature abstraction for a single frontend with a single consumer. This costs build time and onboarding friction, and buys nothing.
- **Leaky boundary**: business logic scattered across React components and service methods, with no layer testable on its own. This is the expensive one, because fixing it means redesigning the boundary rather than moving files.

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

**One caveat specific to v3 before reaching for C**: the toolchain already builds the same codebase as a GUI-less HTTP server (`wails3 task build:server`, `-tags server`), and it can target iOS and Android. Neither of those is a second consumer in profile C's sense — they're the same application on another surface, built from the same root package, and neither justifies a multi-binary layout on its own. See §9 of the reference for what the server target does and does not solve.

**If that second consumer is a CLI companion to the desktop app, there are two ways to build it — never default, always ask which one fits:**

| | Single binary, dual-mode | Two separate binaries |
|---|---|---|
| What ships | One executable — runs as CLI with arguments, opens the window with none | Two executables |
| CLI weight | Carries the GUI framework compiled in, even when running as CLI | Lean — the CLI binary doesn't depend on Wails at all |
| Guarantee against GUI code leaking into CLI logic | None but discipline — same compilation unit | Enforced by the compiler — the CLI's `main` package has no Wails dependency, so it can't happen |
| Folder shape needed | None beyond profile B's — see `references/architecture.md` §3.B-CLI | Profile C's shape — see §3.C |
| Fits best | Simple distribution, no heavy scripted/looped use | CLI invoked repeatedly in scripts or CI, where startup weight matters |

This matters structurally, not just for naming: the single-binary option doesn't need profile C's shape at all — it stays inside profile B with one added file.

## The six decisions

Settle these before creating folders. Full detail is in `references/architecture.md` (§4).

| # | Decision | Default answer |
|---|---|---|
| W1 | Where does business logic live? | Follows the profile |
| W2 | Shape of the service surface | Thin service methods, use-case oriented, minimal exported surface (see security note above) |
| W3 | Go-side state | Struct fields on the service type; `sync.Mutex`/`RWMutex` if shared across goroutines; channels for anything actor-shaped |
| W4 | Error boundary | Typed error result (a struct with a stable `Code`), never a bare `error` returned raw to JS |
| W5 | Long-running work | Registered typed events (`application.RegisterEvent[T]`, `app.Event.Emit`); per-call ordering via a request ID when needed |
| W6 | Frontend location | `frontend/` — the Wails default, already a subfolder, no configuration cost |

W2 is the structuring one — spend the effort there. The other five follow from it or from the profile.

## Workflow: scaffolding a new project

1. **Determine the profile.** Ask about: what the app does, expected system access, team size, and whether a second consumer of the business logic is planned. Don't assume.
2. **Propose before building.** State the recommended profile and W1–W6 values, get agreement.
3. **Read `references/architecture.md`** (§3 for the tree, §5 for scaffolding rules) and **`references/react-conventions.md`** for the frontend side — it defines the `ipc/` / `bindings/` split, the server-state layer, the error handling layers, and the state management default.
4. **Scaffold with `wails3 init -t react`** rather than writing the tree by hand, then move the generated service into the shape §3 describes. The generated `build/` tree and Taskfiles are load-bearing — don't reconstruct them from memory.
5. **Create only what is used.** No empty folders, no placeholders for unjustified layers.
6. **Keep service methods thin.** A service method should: receive the call, invoke `internal/domain`, map the error into the typed result, return. If a service method's body is doing real logic rather than delegating, the boundary has already leaked — and so has the mirror-image mistake of one method per domain function, which turns the service surface into a copy of the domain API instead of a use-case one.
7. **Design the error type early.** A shared `Result[T]`-shaped struct or a `Code`+`Message` error struct, used consistently across every service method — retrofitting this after several methods return bare strings is expensive.
8. **Be deliberate about the exported surface.** Since there's no capability sandbox, review what's registered and what's exported as if it were the permission boundary — because it is one, in practice.
9. **Generate nothing tied to a forge or CI system.**
10. **Document W1–W6 in the project README.**

## Workflow: auditing an existing project

1. **Confirm it's a v3 codebase** (`Services:` in `main.go`, `frontend/bindings/`, a `Taskfile.yml`). If it's v2, say so and stop — this skill doesn't cover it.
2. **Read `references/architecture.md`** (§6 anti-patterns, §4 decisions) and `references/react-conventions.md` (§8 shared frontend anti-patterns).
3. **Identify the actual profile** and the gap with the appropriate one.
4. **Walk the anti-pattern checklist**, present/absent/not applicable, with file and line as evidence.
5. **Check the service surface specifically**: is every exported method on a registered service something the app genuinely needs exposed, or is a broad service registered "for convenience"? This is easy to miss because there is no manifest file to review — the permission surface has to be read from the `Services:` list and the methods' capitalization.
6. **Assess W1–W6 as actually implemented.**
7. **Rank findings by increasing cost to fix.**
8. **Modify no files** unless asked.

## Workflow: migration and refactoring

One misconception to correct up front: **there is no easy migration from B to C.** What changes is the shape of the boundary, not where code sits — moving files without redesigning the boundary produces profile C's cost with profile B's coupling.

1. **Check the prerequisite**: is `internal/domain` free of any Wails import? v3 no longer forces a `context` on service methods, so this is usually cleaner than it was in v2 — but check for event emission and application/window calls reaching down into domain code.
2. **Describe the target boundary before moving code** — service methods, payloads, error types, event contracts.
3. **Extract module by module.**
4. For a targeted fix, change **only** the anti-pattern named.

## Workflow: evolving toward a server with remote clients

Three points need surfacing, because none are covered by W1–W6 and all three are easy to get wrong:

1. **Not everything in `internal/domain` can centralize** — local file/process access stays client-side; classify module by module.
2. **Design W2 as if it were already a network API** — use-case-oriented service methods reuse cleanly as HTTP handlers later (Go makes this concretely easy: a service method and an HTTP handler can share the same underlying `internal/domain` call with very little adaptation).
3. **Multi-user auth and data isolation are unaddressed by anything here** — and this is *more* pressing in v3, not less, because `wails3 task build:server` will hand you a running HTTP server from the same code in one command. That build serves one application to whoever reaches it; it grants no notion of users, sessions, or isolation between them. Treat that as a separate design pass, and say so before anyone mistakes the server target for a multi-client architecture.

## Reference files

- `references/architecture.md` — folder trees per profile, the six decisions in detail, the anti-pattern checklist, evolution path, server-evolution detail, standalone prompts.
- `references/react-conventions.md` — frontend conventions for the React side: folder shape, server state, error handling layers, state management default, testing approach.

For scaffolding, architecture.md §3/§5 plus the React reference are usually enough. For an audit, §6/§4 plus the React reference's §8.
