---
name: rust-webview-desktop-architecture
description: Choose, scaffold, and audit the architecture of a Tauri 2 desktop app (React + Vite + Rust). Use when building, structuring or reviewing one — where logic sits between the frontend and Rust, splitting into crates or a monorepo, Tauri commands, IPC boundaries, src-tauri, capabilities, invoke() organization. Assumes Tauri is already chosen; if no stack has been settled on, use desktop-app-architecture first.
---

# Tauri Architecture

Pick an architecture profile for a Tauri 2 desktop app, scaffold it, or audit an existing one against it.

## Scope

This skill covers one specific stack: **Tauri 2 (React + Vite + Rust)**. If the user hasn't settled on Tauri yet — they're just asking how to build "a desktop app" without naming a stack — defer to the `desktop-app-architecture` skill, which helps pick a stack and will route back here once Tauri is the answer.

## Core idea

The folder tree is a **consequence**, not a decision. What actually determines a Tauri project's shape is where business logic lives and what shape the IPC boundary takes. A badly shaped boundary is not fixed by reorganizing folders, so settle the boundary before creating directories.

Two failure modes to guard against, because both are common and both are expensive:

- **Over-structuring**: crates, monorepo, and shared packages created for a single frontend with a single consumer. This costs build time, dependency pain, and onboarding friction, and buys nothing.
- **Leaky boundary**: business logic scattered across React components and Tauri commands, with no layer that can be tested on its own. This is the one that gets expensive later, because fixing it means redesigning the boundary rather than moving files.

## The three profiles

Use the evocative names when talking to the user — they carry the intuition without requiring stack knowledge.

| Profile | Idea | Business logic | Use when |
|---|---|---|---|
| **A. The Storefront** | You look through it; nothing is made on site | React | UI over a remote API, little or no system access |
| **B. The Workshop** | Someone works at a bench with the machine's tools | React (workflows) + Rust (system) | Files, Git, processes, local DB — **default choice** |
| **C. The Engine** | Self-contained mechanics that can power several vehicles | Rust, in crates | A real second consumer exists (CLI, server, other frontend) |

Decision rules:

- **Default to B.** It absorbs early uncertainty best and is what most desktop apps actually need.
- Choose **A** only when there is no meaningful system access.
- Choose **C** only when a second consumer is real and identified — including a server that will expose the same business logic to remote clients. "We might need it later" is not a second consumer — this is the most common over-structuring mistake.

**If that second consumer is a CLI companion to the desktop app, there are two ways to build it — never default, always ask which one fits:**

| | Single binary, dual-mode | Two separate binaries |
|---|---|---|
| What ships | One executable — runs as CLI with arguments, opens the window with none | Two executables |
| CLI weight | Carries the GUI framework compiled in, even when running as CLI | Lean — the CLI binary doesn't depend on Tauri at all |
| Guarantee against GUI code leaking into CLI logic | None but discipline — same compilation unit | Enforced by the compiler — the CLI crate has no Tauri dependency, so it can't happen |
| Folder shape needed | None beyond profile B's — see `references/architecture.md` §3.B-CLI | Profile C's workspace shape — see §3.C |
| Fits best | Simple distribution, no heavy scripted/looped use | CLI invoked repeatedly in scripts or CI, where startup weight matters |

This matters structurally, not just for naming: the single-binary option doesn't need profile C's workspace/crates shape at all — it stays inside profile B with one added module. The heavier multi-crate structure below is specifically what the two-binaries choice requires.

A note on scope: a local HTTP sidecar (Rust process exposing HTTP instead of Tauri's `invoke()`) is occasionally seen in the wild, but it's rare enough, and different enough in its concerns (port management, process lifecycle, no mobile path), that it isn't documented here as a profile. If the user's project genuinely needs one, treat it as a one-off design problem rather than reaching for a template.

## The seven decisions

Settle these before creating folders. Full detail is in `references/architecture.md` (§4).

| # | Decision | Default answer |
|---|---|---|
| D1 | Where does business logic live? | Follows the profile |
| D2 | Shape of the IPC boundary | Thin commands, use-case oriented |
| D3 | Rust-side state | Stateless; `State<Mutex<T>>` if shared; actor beyond 2–3 mutexes |
| D4 | Error boundary | Typed serializable enum, never `String` |
| D5 | Long-running work | Events or channels beyond ~500 ms |
| D6 | Shared typing | Generated from Rust (`tauri-specta` / `ts-rs`) |
| D7 | Frontend location | Root for A and B, `apps/*` for C |

D2 is the structuring one. When in doubt, spend the effort there.

## Workflow: scaffolding a new project

1. **Determine the profile.** Ask about: what the app does, expected system access (files / Git / processes / local DB / none), team size and Rust experience, and whether any second consumer of the business logic is planned. If the answers are missing, ask — do not assume. Guessing the profile is the one mistake that propagates into every folder.
2. **Propose before building.** State the recommended profile with justification and proposed values for D1–D7. Get agreement first. Scaffolding an unwanted monorepo wastes far more of the user's time than one round of confirmation.
3. **Read `references/architecture.md`** (§3 for the tree, §5 for the scaffolding rules).
4. **Create only what is used.** An empty folder is noise. No placeholder files for layers that aren't yet justified.
5. **Create `error.rs` and `state.rs` from profile B onward**, even if nearly empty. These are the boundaries most expensive to introduce late.
6. **Keep `main.rs` to bootstrap only**; all setup goes in `lib.rs`. Anything else blocks mobile targets and makes the app untestable.
7. **Write a minimal capability** in `src-tauri/capabilities/`. Never a broad or permissive one — a wide capability cancels most of Tauri's security model.
8. **Generate nothing tied to a forge or CI system.** No `.github/`, no `.gitlab-ci.yml`, no pipeline files, unless the user explicitly asks.
9. **Document the chosen D1–D7 in the project README**, so the next person inherits the reasoning and not just the folders.

## Workflow: auditing an existing project

1. **Read `references/architecture.md`** (§6 anti-patterns, §4 decisions).
2. **Identify the actual profile** the codebase implements, and the gap with the profile it should have. A project claiming to be an Engine with one frontend and no CLI is really a Workshop carrying monorepo overhead.
3. **Walk the anti-pattern checklist**, marking each present / absent / not applicable, with file and line as evidence. Evidence matters — an audit without file references can't be acted on.
4. **Assess D1–D7 as actually implemented**, not as documented.
5. **Rank findings by increasing cost to fix**, so the user can start with what's cheap.
6. **Modify no files** during an audit unless the user asks for fixes. An audit that silently rewrites code can't be trusted or reviewed.

Priority when reporting: leaky boundaries (anti-patterns 1, 2, 3, 11) matter more than naming or layout issues, because they are the ones that compound.

## Workflow: migration and refactoring

Correct a common misconception here: **there is no easy migration from B to C.** What changes is not where code sits but the shape of the boundary. So:

1. **Check the prerequisite first**: is `domain/` free of any Tauri dependency? If not, list the dependencies to break before extracting anything. Extraction before this is done is what makes the operation expensive.
2. **Describe the target boundary before moving code** — commands, payloads, errors, progress reporting. Get agreement on the boundary, then implement.
3. **Extract module by module**, never wholesale.
4. **Justify each new crate**: size, boundary stability, and consumers. A crate under ~200 lines with one consumer is premature.
5. For a targeted fix, change **only** the anti-pattern named, and explain the change before applying it.

## Workflow: evolving toward a server with remote clients

This is a distinct scenario from the B→C migration above: the goal isn't reuse on the same machine, it's a server that remote clients connect to. Profile C is the right target, but three things need to be surfaced explicitly — they aren't covered by D1–D7 and are easy to miss.

1. **Separate what's centralizable from what's inherently local.** Profile B's value often comes from *local* system access — files, Git, processes on the user's machine. That logic cannot simply move to a server: a remote server has no access to a client's filesystem. Go through `domain/` module by module and classify each as centralizable (becomes real server-side data, e.g. in a database) or inherently local (stays client-side, and the desktop app becomes one client among others). This is a product decision, not a mechanical refactor — don't assume everything centralizes by default.
2. **Design the D2 boundary as if it were already a network API.** Use-case-oriented, typed, versionable commands are exactly the shape needed later for an HTTP layer. Work spent tightening D2 now is reused directly when the server is built — sloppy D2 today becomes a second design pass later.
3. **Flag multi-user auth and data isolation as a separate, unaddressed concern.** Tauri's capability model governs what a local process may do on its own machine — it says nothing about which remote user may see which data on a shared server. Authentication, sessions, and tenant isolation need their own design pass; don't assume the capabilities model extends to it.

## Reference file

Read `references/architecture.md` when you need the folder trees, the full decision detail, or the audit checklist. It contains: §1 decisions, §2 profile selection, §3 folder trees per profile, §4 cross-cutting decisions in detail, §4b runtime data and log locations, §5 scaffolding rules, §6 the anti-pattern checklist, §7 evolution path, §8 standalone prompts, §9 evolving toward a server with remote clients.

Read `references/react-conventions.md` for the frontend side — folder shape (`ipc/`, `bindings/`, `features/`), the server-state layer, error handling layers, state management default, and testing approach. React is the mandated frontend for this stack, and the frontend should look the same regardless of which backend is behind it.

For scaffolding, §3 and §5 plus the React reference are usually enough. For an audit, §6 and §4 plus the React reference's §8.
