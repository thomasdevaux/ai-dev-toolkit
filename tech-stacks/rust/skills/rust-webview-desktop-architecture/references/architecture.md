# Reference — Tauri 2 Project Architecture (React + Vite + Rust)

Selection grid, target folder structures, and audit checklist.
Forge-neutral (GitHub, GitLab, Forgejo...). No CI considerations.

**Contents**
1. The decisions that matter (D1–D7)
2. Choosing a profile
3. Profiles and folder structures
4. Cross-cutting decisions in detail
4b. Where the app writes at runtime
5. Scaffolding rules
6. Anti-patterns — audit checklist
7. Evolution path
8. Prompts (standalone use)
9. Evolving toward a server with remote clients

---

## 1. The decisions that actually matter

The folder tree is a **consequence**, not a decision. The real decisions, to settle before creating the first folder:

| # | Decision | Options | Impact |
|---|---|---|---|
| D1 | Where does business logic live? | React / split / Rust | Determines the profile |
| D2 | Shape of the IPC boundary | thin commands / use-case commands | Very expensive to change later |
| D3 | Rust-side state | stateless / `State<Mutex<T>>` / `State<RwLock<T>>` / actor (mpsc) | Testability and deadlocks |
| D4 | Error boundary | `String` / typed serializable enum | Whether the frontend can react precisely |
| D5 | Long-running / progress | blocking commands / events / channels | UX on heavy tasks |
| D6 | Shared typing | manual / generated (`tauri-specta`, `ts-rs`) | Front/back drift over time |
| D7 | Frontend location | root (Tauri default) / `apps/*` (two-binaries variant) | Configuration cost |

**D2 is the structuring decision.** A badly shaped IPC boundary is not fixed by reorganizing folders.

---

## 2. Choosing a profile

| Criterion | A. The Storefront | B. The Workshop | C. The Engine |
|---|---|---|---|
| Business logic | React | React (workflow) + Rust (system) | Rust |
| System access | Low or none | Frequent | Central |
| Reuse outside desktop | No | Rare | Explicit goal, including a server exposing the logic to remote clients |
| Team size | 1–3, front only | Small mixed team | Dedicated Rust skills |
| Maturity | Prototype / MVP | Growing product | Platform / engine |
| Tooling complexity | Low | Moderate | High (workspaces) |
| Tauri 2 mobile targets | Unlikely | Possible | Common |

**The metaphors** — use these when explaining to someone unfamiliar with the stack:

- **The Storefront**: you look through it; nothing is made on site. Everything comes from elsewhere.
- **The Workshop**: someone works at a bench with the machine's tools.
- **The Engine**: self-contained mechanics that can power several vehicles; the screen is just a dashboard.

### Decision rules

- **Default: B (The Workshop).** It absorbs early uncertainty best.
- **A** only if the app is an interface over a remote API with no significant system access.
- **C** only if there is a **real, identified second consumer** (CLI, server, another frontend — including a server meant to expose the same business logic to remote clients). Not "just in case".

### Out of scope: local HTTP sidecar

A Rust process exposing HTTP locally instead of using Tauri's `invoke()` shows up occasionally (e.g. wrapping a pre-existing HTTP backend, or aiming for web/desktop parity). It's rare enough, and different enough in its concerns — port management, process lifecycle, packaging, no viable mobile path — that it isn't documented here as a profile. Treat it as a one-off design problem if it comes up, not a template to reach for.

---

## 3. Profiles and folder structures

### A. The Storefront

Rust limited to bootstrapping. Frontend at root (Tauri default, zero extra configuration).

```text
my-app/
├── src/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   ├── api/                  # remote HTTP calls
│   ├── lib/
│   ├── App.tsx
│   └── main.tsx
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
│
├── src-tauri/
│   ├── src/
│   │   ├── lib.rs            # Tauri setup, plugins, builder
│   │   └── main.rs           # calls lib.rs, nothing else
│   ├── capabilities/
│   │   └── default.json
│   ├── icons/
│   ├── tauri.conf.json
│   └── Cargo.toml
│
├── .env.example
└── README.md
```

**Target**: MVP, dashboard, REST client, simple tool.

**Constraints**:
- `main.rs` contains only the call into `lib.rs` (mobile targets, testability).
- Don't create `commands/` until there are at least 2–3 real commands.

---

### B. The Workshop (recommended default)

React handles UI and workflows. Rust handles system access, persistence, and heavy processing.

```text
my-app/
├── src/                          # frontend (at root, Tauri default)
│   ├── components/               # pure presentation, no IPC
│   ├── features/                 # split by business domain
│   │   └── <feature>/
│   │       ├── components/
│   │       ├── hooks/
│   │       └── index.ts
│   ├── pages/
│   ├── ipc/                      # THE ONLY place invoke() is called
│   │   ├── client.ts             # typed wrapper + error mapping
│   │   └── <domain>.ts
│   ├── store/                    # global state (zustand / jotai / redux)
│   ├── bindings/                 # types generated from Rust — do not edit
│   ├── lib/                      # pure utilities
│   ├── App.tsx
│   └── main.tsx
├── public/
├── index.html
├── vite.config.ts
├── package.json
│
├── src-tauri/
│   ├── src/
│   │   ├── commands/             # thin IPC boundary, no logic
│   │   │   ├── mod.rs
│   │   │   └── <domain>.rs
│   │   ├── domain/               # business logic, testable without Tauri
│   │   │   ├── mod.rs
│   │   │   └── <domain>/
│   │   ├── infra/                # adapters: fs, git, process, http
│   │   ├── db/
│   │   │   ├── mod.rs
│   │   │   └── migrations/
│   │   ├── state.rs              # AppState + locking policy
│   │   ├── error.rs              # serializable error enum (D4)
│   │   ├── lib.rs                # Tauri builder, manage(), handlers
│   │   └── main.rs
│   ├── tests/                    # integration tests
│   ├── capabilities/
│   │   └── default.json
│   ├── icons/
│   ├── tauri.conf.json
│   └── Cargo.toml
│
├── .env.example
└── README.md
```

**Split of responsibilities**:

| React | Rust |
|---|---|
| UI, navigation, forms, screen state | Files, Git, processes, low-level networking |
| User journey orchestration | Persistence (SQLite), migrations |
| Display validation | Authoritative business validation |
| — | CPU-bound processing, heavy parsing |

**`domain/` vs `infra/`**: this split replaces the generic `services/`, which is ambiguous because a `services/` folder often exists on both sides with two different roles. It makes explicit what is testable without I/O (`domain/`) and what touches the outside world (`infra/`). It's also the split that survives best if the code is later extracted into crates.

**Target**: IDEs, developer tooling, document management, classic desktop apps.

---

### B — variant: CLI access without a second binary

When a CLI companion is wanted but the single-binary, dual-mode option was chosen (see the decision table in `SKILL.md`), this stays entirely inside profile B's shape — no workspace, no `crates/`. Only `src-tauri/` changes:

```text
src-tauri/
├── src/
│   ├── commands/          # unchanged — Tauri commands, GUI path only
│   ├── domain/             # unchanged — shared by both paths
│   ├── infra/               # unchanged
│   ├── cli.rs                # argument parsing (clap) and CLI-mode dispatch
│   ├── state.rs
│   ├── error.rs
│   ├── lib.rs
│   └── main.rs                # branches before launching Tauri — see below
```

```rust
// main.rs
fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() > 1 {
        return cli::run(&args[1..]);   // CLI mode — never touches Tauri
    }
    myapp_lib::run();                   // no args — launch the window as usual
}
```

Both paths call the same `domain/` functions. Nothing here needs Tauri's builder to run for the CLI path, so no window is created in that mode. The trade-off from the decision table still applies: the compiled binary includes Tauri regardless of which path executes, and nothing but code review stops CLI code from accidentally reaching into `commands/` or GUI-only state.

---

### C. The Engine — variant: two separate binaries

Business logic entirely in Rust, organized into crates, consumed by genuinely separate binaries. This is the heavier structure — only reach for it when the two-separate-binaries choice was made deliberately (see the decision table in `SKILL.md`), not merely because a CLI was wanted at all.

```text
my-app/
├── apps/
│   ├── desktop/
│   │   ├── src/                  # UI, only calls commands
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── package.json
│   │   └── src-tauri/
│   │       ├── src/
│   │       │   ├── commands/     # thin exposure over crates
│   │       │   ├── state.rs
│   │       │   ├── error.rs
│   │       │   ├── lib.rs
│   │       │   └── main.rs
│   │       ├── capabilities/
│   │       ├── tauri.conf.json
│   │       └── Cargo.toml
│   └── cli/                      # 2nd binary — has no Tauri dependency at all
│       ├── src/main.rs
│       └── Cargo.toml
│
├── crates/
│   ├── core/                     # types, errors, traits, config
│   ├── domain/                   # pure business rules
│   └── <capability>/             # git, filesystem, ai... on evidence
│
├── packages/                     # ONLY if ≥ 2 frontends
│   └── shared-types/             # TS types generated from the crates
│
├── docs/
├── scripts/
├── rust-toolchain.toml
├── Cargo.toml                    # root [workspace]
├── pnpm-workspace.yaml
└── package.json
```

**`apps/`**: follows the JS-monorepo convention (Turborepo, Nx) that Tauri's own multi-app examples already lean on, since a Tauri project is a hybrid Rust+JS project rather than a pure Rust one. Each subfolder is a separate compiled binary with its own `Cargo.toml`.

**Constraints**:
- Only create a crate when a module exceeds ~500 lines **and** has a stable boundary. Start with `core` alone. A set of 200-line crates degrades build times and creates circular dependency pain while buying nothing.
- `packages/ui/` is only justified with two real frontends. Otherwise it's abstraction debt.
- The `src-tauri` crate must be a workspace member; check path resolution in `tauri.conf.json` and the `Cargo.lock` location.
- `apps/cli` (or equivalent) must exist or be planned: without a second consumer, this variant isn't justified. And it must actually be the *two-binaries* choice — if a single dual-mode binary would do, use the lighter §3.B variant above instead.

**Target**: complex software, platforms, multi-frontend apps, reusable engines.

**Second consumer is a server**: when the identified second consumer is a server exposing the same business logic to remote clients (rather than a CLI), swap `apps/cli/` for `apps/server/` (an axum binary, or equivalent), consuming the same `crates/domain` and `crates/core`. This is the standard shape for "desktop app today, multi-client server later" — see §9 for what this migration involves beyond the folder move.

---

## 4. Cross-cutting decisions in detail

### D2 — Shape of the IPC boundary
Commands are a serialization boundary, **not** a business layer. A command should: deserialize, call `domain/`, map the error, serialize. If `commands/<x>.rs` mirrors `domain/<x>.rs` function for function, the layer adds nothing: merge it or revisit the split.

Granularity: prefer **use-case oriented** commands (`open_project`) over **technical CRUD** (`read_file`, `parse_config`, `validate_config`). Overly fine-grained commands push business orchestration into React — exactly what profile B is trying to avoid.

### D3 — Rust-side state
- Stateless wherever possible.
- `State<Mutex<T>>` by default for shared state; `RwLock` when reads heavily dominate.
- Never hold a lock across an `.await`.
- Beyond 2–3 interdependent mutexes, move to an **actor** (task + `mpsc`): a single state owner, message-based communication.

### D4 — Error boundary
A serializable error enum with a stable discriminant, not a `String`. The frontend must be able to tell "file not found" from "permission denied" without parsing text. Separate internal errors (logged, detailed) from exposed errors (typed, safe): never leak absolute paths or secrets in the payload.

### D5 — Long-running work
Commands are short request/response. Any operation over ~500 ms should report progress via **events** (broadcast) or **channels** (per-call, ordered, preferable when a single caller awaits the stream). A long blocking command freezes UX and makes cancellation impossible.

### D6 — Shared typing
Generate TS types from Rust (`tauri-specta`, or `ts-rs`) into `src/bindings/`, marked non-editable. Without generation, types drift — a matter of months, not years.

### Security — capabilities (Tauri 2)
Explicit minimal permissions in `src-tauri/capabilities/`. Never widen "to unblock something" without narrowing again afterwards. A broad capability cancels most of Tauri's security model.

### Secrets and configuration
Anything prefixed `VITE_` is in plain text in the bundle: never a secret. API keys live on the Rust side and are not returned through `invoke()`. Version `.env.example`, gitignore `.env`.

### Testing
- Rust: co-located unit tests (`#[cfg(test)]`) on `domain/`; integration tests in `src-tauri/tests/`.
- `domain/` must be testable **without** a Tauri dependency. If it isn't, logic has leaked into `commands/`.
- Frontend: vitest on `features/` and `lib/`, with `ipc/` mocked.

---

## 4b. Where the app writes at runtime

Distinct from where the code lives: where the installed application writes
settings, its database, and its logs. Writing beside the executable works
throughout development and breaks the day the app is installed under
`Program Files`, where the process has no write access — so it surfaces at the
user's site, not on the developer's machine.

Resolve the paths from Tauri's path API — `app_data_dir` for state and the
database, `app_log_dir` for logs, `app_cache_dir` for anything regenerable.
Resolve them once during setup and pass them into `domain/`; domain code should
receive a path, never reach for the app handle to compute one, which is exactly
the dependency that stops it being testable without Tauri.

---

## 5. Scaffolding rules

1. Determine the profile via §2. If information is insufficient, **ask** — do not assume.
2. Only create folders that are actually used. An empty folder is noise — no placeholders for layers that aren't yet justified.
3. `main.rs`: bootstrap only; all setup logic in `lib.rs`.
4. Create `error.rs` and `state.rs` from profile B onward, even minimal: these are the boundaries most expensive to introduce late.
5. Create `capabilities/default.json` with minimal permissions, never a broad capability.
6. Don't move the frontend out of the root for profiles A and B unless explicitly requested: the configuration cost (`frontendDist`, `devUrl`, build command cwd) isn't justified with a single frontend.
7. Don't create `crates/` or `packages/` without an identified second consumer.
8. Generate nothing tied to a forge or CI system.
9. Document the chosen D1–D7 values in the project `README.md`.
10. **Leave build artifacts where Cargo and Tauri put them.** The other stacks in this portfolio route their output to `dist/release/` and `dist/debug/`; this branch deliberately opts out, for two reasons specific to it:

    - Cargo owns `target/` as an incremental build cache and offers no "final artifact goes here" setting, so the convention would only hold via a post-build copy — extra machinery, a duplicated artifact, and a `cp`/`copy` split to maintain.
    - `dist/` is already taken. Vite's default `build.outDir` is `dist/`, and profiles A and B put the frontend at the repository root, so the name would refer to the frontend bundle and the shipped executable at the same path.

    So: `target/release/<name>` for the binary, `target/release/bundle/<format>/` for the installers `tauri build` produces, and `dist/` left to Vite. Say this plainly in the project README, since someone arriving from the Python, Go or .NET tools in this portfolio will look for `dist/` first.

---

## 6. Anti-patterns — audit checklist

| # | Symptom | Diagnosis |
|---|---|---|
| 1 | `invoke()` called from components | No `ipc/` layer — UI/backend coupling |
| 2 | `commands/` mirrors `domain/` 1:1 | Layer with no added value |
| 3 | Business logic inside `commands/` | `domain/` not testable without Tauri |
| 4 | Errors returned as `String` | Frontend can't react precisely (D4) |
| 5 | Hand-written TS types for payloads | Guaranteed front/back drift (D6) |
| 6 | Broad or permissive capability | Tauri security model neutralized |
| 7 | Many crates under 200 lines | Premature split, degraded builds and deps |
| 8 | `packages/ui/` with a single frontend | Abstraction debt |
| 9 | Blocking command > 1 s with no progress | Frozen UX, no cancellation (D5) |
| 10 | Lock held across an `.await` | Deadlock risk (D3) |
| 11 | Business logic duplicated in React and Rust | D2 boundary never settled |
| 12 | Secrets reachable from the frontend | Leak in the bundle |
| 13 | `main.rs` containing full setup | Mobile targets and tests blocked |
| 14 | Both `src/services/` and `src-tauri/services/` | Naming ambiguity, two different roles |
| 15 | Missing or manual DB migrations | Non-reproducible schema |
| 16 | Writes configuration, database or logs beside the executable | Breaks on any read-only or per-machine install; surfaces only after deployment (§4b) |

**Reporting priority**: leaky boundaries (1, 2, 3, 11) before naming or layout issues — those are the ones that compound over time.

---

## 7. Evolution path

Important point: **you don't "migrate" easily from B to C.** What changes isn't where the code sits but the **shape of the boundary**. The strategy that works:

1. Start with **B**, with `domain/` already separated from `commands/` and no Tauri dependency inside `domain/`.
2. Keep logic in React as long as it's purely UI-related.
3. Put every authoritative business rule in `domain/`, even when the code is short.
4. Introduce a Cargo workspace when a `domain/` module has a stable boundary **and** a second consumer exists.
5. Extract into `crates/` module by module — the operation is mechanical **if** step 1 was respected, expensive otherwise.

Don't move to C without a real second consumer: monorepo tooling cost isn't amortized by a single frontend.

---

## 8. Prompts (standalone use)

Useful if this file is provided on its own, without the skill.

**New project, profile to determine**
```
Project: <2-3 sentence description>
Expected system access: <files / git / processes / DB / none>
Team: <size, Rust skills or not>
Planned other consumer of the business logic: <yes/no, which>

Step 1: recommend a profile (A/B/C/D) with justification, and propose values
for D1–D7. Create no files.
Step 2: after approval, scaffold the structure following the rules in §5.
```

**Full audit**
```
Audit this project:
1. Identify the actual profile (A/B/C/D) and the gap with the appropriate one.
2. Walk the §6 checklist point by point: present / absent / not applicable,
   with files and line numbers as evidence.
3. Assess D1–D7 as currently implemented.
4. Rank the issues by increasing cost to fix.
Modify no files.
```

**Targeted audit of the IPC boundary**
```
Per §4 (D2) and §6, analyze the IPC boundary:
- do commands contain business logic?
- are they use-case oriented or technical CRUD?
- has business orchestration leaked into React?
- is domain/ testable without Tauri?
Give a verdict per command and an ordered remediation plan.
```

**Profile justification check**
```
This project uses a monorepo with crates/ and packages/.
Per §2 and §3.C, is this profile justified? Check: real second consumer?
crates above the split threshold? packages/ with ≥ 2 consumers?
If not justified, propose a simplification plan toward profile B.
```

**Moving from B to C**
```
Assess extracting src-tauri/src/domain/ into crates/ per §7.
Check the prerequisite first: is domain/ independent of Tauri?
If not, list the dependencies to break before any extraction.
If yes, propose a crate split with per-module justification
(size, boundary stability, consumers).
```

**Evolving toward a server with remote clients**
```
Assess exposing this app's business logic to remote clients via a server,
per §9. Cover:
1. Which domain/ modules are centralizable vs inherently local (filesystem,
   Git, local processes) — classify module by module, don't assume everything
   centralizes.
2. Whether the current D2 boundary (commands) is already use-case oriented,
   typed, and versionable enough to reuse as the shape of an HTTP API.
3. What's still unaddressed: multi-user authentication, session handling,
   data isolation between clients — none of this is covered by the
   capabilities model, which governs local permissions only.
Produce a plan, don't move code yet.
```

---

## 9. Evolving toward a server with remote clients

This is a different scenario from the B→C migration in §7: the goal here isn't reuse on the same machine, it's a server that remote clients connect to over a network. Profile C (with `apps/server/` instead of, or alongside, `apps/cli/`) is the right target — but three things need to be surfaced explicitly, because none of them are covered by D1–D7 and all three are easy to get wrong by assuming the B→C mechanics apply unchanged.

### 1. Not everything in `domain/` can centralize

Profile B's value often comes from *local* system access: files, Git, processes on the user's own machine. That kind of logic cannot simply move to a server, because a remote server has no access to a client's filesystem. Before extracting anything, go through `domain/` module by module and classify each piece:

- **Centralizable**: becomes real server-side state (e.g. rows in a database), the same for every client.
- **Inherently local**: stays on the client. The desktop app becomes one client among others — including, potentially, a future web client — talking to the server for the centralized parts while keeping local operations local.

This is a product decision made module by module, not a mechanical refactor. Don't assume the whole of `domain/` centralizes by default — that assumption is the most common way this migration goes wrong.

### 2. Design D2 as if it were already a network API

Use-case-oriented, typed, versionable commands (see §4, D2) are exactly the shape a good HTTP API needs later. Time spent tightening the IPC boundary now is not local-only investment — it gets reused directly when the server is built. Conversely, a sloppy D2 boundary today (fine-grained CRUD commands, untyped payloads) means redesigning the API boundary from scratch later, on top of the original redesign.

### 3. Multi-user auth and data isolation are a separate, unaddressed problem

Tauri's capability model (see §4, Security) governs what a local process may do on its own machine. It says nothing about which remote user is allowed to see or modify which data on a shared server. Authentication, session management, and tenant/data isolation between clients need their own design pass — they are not an extension of the capabilities model, and nothing in D1–D7 covers them. Treat this as a separate piece of design work, not a byproduct of moving to profile C.
