---
name: go-webview-desktop-architecture
description: Choose, scaffold, and audit the architecture of a Wails desktop app (Go + React). Use this skill whenever the user is building, structuring, or reviewing a Wails app, asks how to organize a Wails/Go/React codebase, wants a review of an existing desktop app's structure, asks where business logic should live between the frontend and Go, wonders whether to split Go code into packages or adopt a multi-app layout, or mentions Wails bindings, the Bind() call, wails.json, or Go↔JS event communication. If the user wants a desktop app but hasn't chosen a stack yet, use the desktop-app-architecture skill first — this skill assumes Wails has already been chosen. React is the mandated frontend for this stack; if the user wants a different frontend framework with Wails, the folder conventions here still mostly apply but the shared React reference does not.
---

# Wails Architecture

Pick an architecture profile for a Wails desktop app (Go backend, React frontend), scaffold it, or audit an existing one against it.

## Scope

This skill covers **Wails v2** (stable) as the default, with v3 noted where it changes things meaningfully — v3 is late alpha as of mid-2026: API is reasonably stable and production apps ship on it, but it's still pre-1.0 and details move. Default to v2 unless the user explicitly wants v3's architecture (multi-window, services-as-`http.Handler`) and accepts the churn that comes with alpha status. Never mix v2 and v3 patterns in the same project — check which one a codebase uses before writing anything, don't guess from phrasing.

If the user hasn't settled on Wails yet, defer to the `desktop-app-architecture` skill.

## Core idea

Same principle as the Tauri skill this one is deliberately parallel to: the folder tree is a **consequence**, not a decision. What determines a Wails project's shape is where business logic lives and what shape the Go↔JS boundary takes.

Two failure modes to guard against:

- **Over-structuring**: multiple Go packages, a multi-app layout, or premature abstraction for a single frontend with a single consumer.
- **Leaky boundary**: business logic scattered across React components and bound Go methods, with no layer testable on its own.

## Two things Wails does differently from Tauri — know these before applying the rest

- **Typed bindings are built into the toolchain.** `wails generate module` (run automatically by `wails dev`) generates JS/TS bindings directly from your Go structs' public methods — no third-party plugin needed, unlike Tauri where `tauri-specta` is an added dependency. This means the Tauri skill's D6 ("generate shared types, don't write them by hand") is close to a non-decision in Wails: the tooling does it by default. Don't skip it anyway by hand-writing types that duplicate what's already generated.
- **There is no capabilities/permissions system.** Tauri 2's `capabilities/*.json` sandbox has no Wails equivalent — any Go method exposed via `Bind()` runs with the full privileges of the Go process, full stop. The practical substitute is discipline about what you bind: treat the set of bound structs and their public methods as your de facto permission surface, and keep it as narrow as the app actually needs. This is worth stating explicitly to the user rather than leaving as an implicit gap, especially for anyone coming from Tauri who might assume an equivalent sandbox exists.

## The three profiles

Same evocative names as the Tauri skill, for consistency across the two web-tech stacks.

| Profile | Idea | Business logic | Use when |
|---|---|---|---|
| **A. The Storefront** | You look through it; nothing is made on site | React | UI over a remote API, little or no system access |
| **B. The Workshop** | Someone works at a bench with the machine's tools | React (workflows) + Go (system) | Files, Git, processes, local DB — **default choice** |
| **C. The Engine** | Self-contained mechanics that can power several vehicles | Go, in shared packages | A real second consumer exists (CLI, server, other frontend) |

Decision rules — identical logic to the Tauri skill:

- **Default to B.**
- **A** only when there's no meaningful system access.
- **C** only when a second consumer is real and identified — including a server exposing the same logic to remote clients (see §9 of the reference file). Not "we might need it later."

**If that second consumer is a CLI companion to the desktop app, there are two ways to build it — never default, always ask which one fits:**

| | Single binary, dual-mode | Two separate binaries |
|---|---|---|
| What ships | One executable — runs as CLI with arguments, opens the window with none | Two executables |
| CLI weight | Carries the GUI framework compiled in, even when running as CLI | Lean — the CLI binary doesn't depend on Wails at all |
| Guarantee against GUI code leaking into CLI logic | None but discipline — same compilation unit | Enforced by the compiler — the CLI's `main` package has no Wails dependency, so it can't happen |
| Folder shape needed | None beyond profile B's — see `references/architecture.md` §3.B-CLI | Profile C's multi-binary shape — see §3.C |
| Fits best | Simple distribution, no heavy scripted/looped use | CLI invoked repeatedly in scripts or CI, where startup weight matters |

This matters structurally, not just for naming: the single-binary option doesn't need profile C's shape at all — it stays inside profile B with one added file. The heavier multi-binary structure below is specifically what the two-binaries choice requires.

## The six decisions

Settle these before creating folders. Full detail is in `references/architecture.md` (§4).

| # | Decision | Default answer |
|---|---|---|
| W1 | Where does business logic live? | Follows the profile |
| W2 | Shape of the Go↔JS boundary | Thin bound methods, use-case oriented, minimal binding surface (see security note above) |
| W3 | Go-side state | Struct fields on the App type; `sync.Mutex`/`RWMutex` if shared across goroutines; channels for anything actor-shaped |
| W4 | Error boundary | Typed error result (a struct with a stable `Code`), never a bare `error` returned raw to JS |
| W5 | Long-running work | Wails events (`EventsEmit`/`EventsOn`); per-call ordering via a unique event name carrying a request ID when needed |
| W6 | Frontend location | `frontend/` (Wails default — already a subfolder, no extra config needed, unlike Tauri where root is the default) |

W2 is the structuring one, same as Tauri's D2 — spend the effort there.

## Workflow: scaffolding a new project

1. **Determine the profile.** Ask about: what the app does, expected system access, team size, and whether a second consumer of the business logic is planned. Don't assume.
2. **Propose before building.** State the recommended profile and W1–W6 values, get agreement.
3. **Read `references/architecture.md`** (§3 for the tree, §5 for scaffolding rules) and **`references/react-conventions.md`** for the frontend side — it's shared with the Tauri skill and defines the same `ipc/` / `bindings/` split, error handling layers, and state management default.
4. **Create only what is used.** No empty folders, no placeholders for unjustified layers.
5. **Keep the bound struct(s) thin.** A bound method should: receive the call, invoke `internal/domain`, map the error into the typed result, return. If a bound method's body is doing real logic rather than delegating, that's the same anti-pattern as Tauri's commands mirroring domain 1:1.
6. **Design the error type early.** A shared `Result[T]`-shaped struct or a `Code`+`Message` error struct, used consistently across every bound method — retrofitting this after several methods return bare strings is expensive.
7. **Be deliberate about the binding surface.** Since there's no capability sandbox, review what's bound as if it were the permission boundary — because it is one, in practice.
8. **Generate nothing tied to a forge or CI system.**
9. **Document W1–W6 in the project README.**

## Workflow: auditing an existing project

1. **Read `references/architecture.md`** (§6 anti-patterns, §4 decisions) and `references/react-conventions.md` (§8 shared frontend anti-patterns).
2. **Identify the actual profile** and the gap with the appropriate one.
3. **Walk the anti-pattern checklist**, present/absent/not applicable, with file and line as evidence.
4. **Check the binding surface specifically**: is every bound method something the app genuinely needs exposed, or is a broad struct bound "for convenience"? This is Wails' equivalent of an overly permissive Tauri capability, and it's easy to miss because there's no manifest file to review — it has to be read from the `Bind()` calls themselves.
5. **Assess W1–W6 as actually implemented.**
6. **Rank findings by increasing cost to fix.**
7. **Modify no files** unless asked.

## Workflow: migration and refactoring

Same misconception to correct as in the Tauri skill: **no easy migration from B to C.** What changes is the shape of the boundary, not where code sits.

1. **Check the prerequisite**: is `internal/domain` free of any Wails-runtime imports (`context`, event emission, etc.)? If not, list what to break first.
2. **Describe the target boundary before moving code** — bound methods, payloads, error types, event contracts.
3. **Extract module by module.**
4. For a targeted fix, change **only** the anti-pattern named.

## Workflow: evolving toward a server with remote clients

Same three points as the Tauri skill's §9, adapted:

1. **Not everything in `internal/domain` can centralize** — local file/process access stays client-side; classify module by module.
2. **Design W2 as if it were already a network API** — use-case-oriented bound methods reuse cleanly as HTTP handlers later (Go makes this concretely easy: a bound method and an HTTP handler can share the same underlying `internal/domain` call with very little adaptation).
3. **Multi-user auth and data isolation are unaddressed by anything here** — and more so than in Tauri, since Wails has no capability model to begin with. Treat this as a separate design pass.

## Reference files

- `references/architecture.md` — folder trees per profile, the six decisions in detail, the anti-pattern checklist, evolution path, server-evolution detail, standalone prompts.
- `references/react-conventions.md` — frontend conventions shared with the Tauri skill (identical file in both).

For scaffolding, architecture.md §3/§5 plus the React reference are usually enough. For an audit, §6/§4 plus the React reference's §8.
