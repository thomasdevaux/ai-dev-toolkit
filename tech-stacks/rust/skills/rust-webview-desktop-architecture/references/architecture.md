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
| D7 | Frontend location | `apps/desktop/` in every profile (§3, common layout) | One-off configuration, then identical across projects |

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

### Common layout (every profile)

```text
my-app/
├── apps/
│   └── desktop/                  # the frontend package
│       ├── src/
│       ├── index.html
│       ├── vite.config.ts        # server.port = this app's port, strictPort: true
│       ├── package.json          # format, format:check, lint, typecheck, test
│       └── src-tauri/            # workspace member
├── crates/                       # profiles B and C only
├── Cargo.toml                    # root [workspace]: members, profiles, [workspace.lints]
├── Cargo.lock                    # one lockfile, at the root
├── package.json                  # npm workspace ["apps/desktop"], forwarding scripts
├── package-lock.json
├── rust-toolchain.toml
├── .env.example
└── README.md
```

Configuration this costs once, the same in every project:

- `src-tauri` is a member of the root workspace; `cargo` builds into the root `target/`.
- `tauri.conf.json`: `frontendDist: "../dist"`, `devUrl: "http://localhost:<port>"` with a port of its own per app (two apps on the same port end up showing each other's dev server), `beforeDevCommand` / `beforeBuildCommand` run in `apps/desktop`.
- The root `package.json` forwards each script: `"lint": "npm run lint --workspace=apps/desktop"`, so the gate calls one place.

### A. The Storefront

Rust limited to bootstrapping. No core crate: there is no Rust logic to put in one.

```text
my-app/
├── apps/desktop/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/              # remote HTTP calls
│   │   ├── lib/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── src-tauri/
│       ├── src/
│       │   ├── lib.rs        # Tauri setup, plugins, builder
│       │   └── main.rs       # calls lib.rs, nothing else
│       ├── capabilities/
│       │   └── default.json
│       ├── icons/
│       ├── tauri.conf.json
│       └── Cargo.toml
├── Cargo.toml                # [workspace] members = ["apps/desktop/src-tauri"]
├── package.json
├── rust-toolchain.toml
├── .env.example
└── README.md
```

**Target**: MVP, dashboard, REST client, simple tool.

**Constraints**:
- `main.rs` contains only the call into `lib.rs` (mobile targets, testability).
- Don't create `commands/` until there are at least 2–3 real commands.
- Create `crates/<name>-core` the day Rust holds logic beyond bootstrapping — that is the moment the app becomes a Workshop.

---

### B. The Workshop (recommended default)

React handles UI and workflows. Rust handles system access, persistence, and heavy processing.

```text
my-app/
├── apps/desktop/
│   ├── src/                          # frontend
│   │   ├── components/               # pure presentation, no IPC
│   │   ├── features/                 # split by business domain
│   │   │   └── <feature>/
│   │   │       ├── components/
│   │   │       ├── hooks/
│   │   │       └── index.ts
│   │   ├── pages/
│   │   ├── ipc/                      # THE ONLY place invoke() is called
│   │   │   ├── client.ts             # typed wrapper + error mapping
│   │   │   └── <domain>.ts
│   │   ├── store/                    # global state (zustand / jotai / redux)
│   │   ├── bindings/                 # types generated from Rust — do not edit
│   │   ├── lib/                      # pure utilities
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   └── src-tauri/
│       ├── src/
│       │   ├── commands/             # thin IPC boundary, no logic
│       │   │   ├── mod.rs
│       │   │   └── <domain>.rs
│       │   ├── state.rs              # AppState + locking policy
│       │   ├── error.rs              # serializable error enum (D4)
│       │   ├── lib.rs                # Tauri builder, manage(), handlers
│       │   └── main.rs
│       ├── capabilities/
│       │   └── default.json
│       ├── icons/
│       ├── tauri.conf.json
│       └── Cargo.toml                # depends on <name>-core
│
├── crates/
│   └── <name>-core/                  # no Tauri dependency
│       ├── src/
│       │   ├── domain/               # business logic
│       │   │   └── <domain>/
│       │   ├── infra/                # adapters: fs, git, process, http
│       │   ├── db/
│       │   │   └── migrations/
│       │   └── lib.rs
│       ├── tests/                    # integration tests
│       └── Cargo.toml
│
├── Cargo.toml                        # root [workspace]
├── package.json
├── rust-toolchain.toml
├── .env.example
└── README.md
```

**One core crate, not several.** `domain/`, `infra/` and `db/` are modules of the same crate. Splitting them into crates of their own is profile C, and needs C's justification (§3.C constraints).

**Split of responsibilities**:

| React | Rust |
|---|---|
| UI, navigation, forms, screen state | Files, Git, processes, low-level networking |
| User journey orchestration | Persistence (SQLite), migrations |
| Display validation | Authoritative business validation |
| — | CPU-bound processing, heavy parsing |

**`domain/` vs `infra/`**: this split replaces the generic `services/`, which is ambiguous because a `services/` folder often exists on both sides with two different roles. It makes explicit what is testable without I/O (`domain/`) and what touches the outside world (`infra/`). It's also the split that survives best if the core crate is later divided.

**Why the core crate from day one**: `cargo test -p <name>-core` builds and runs without linking Tauri or a webview, which is faster and smaller, and a Tauri type cannot leak into `domain/` because the crate has no Tauri dependency to import.

**Target**: IDEs, developer tooling, document management, classic desktop apps.

---

### B — variant: CLI access without a second binary

When a CLI companion is wanted but the single-binary, dual-mode option was chosen (see the decision table in `SKILL.md`), this stays entirely inside profile B's shape — no second app, no further crate. Only `apps/desktop/src-tauri/` changes:

```text
src-tauri/
├── src/
│   ├── commands/          # unchanged — Tauri commands, GUI path only
│   ├── cli.rs                # argument parsing (clap) and CLI-mode dispatch, over <name>-core
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

Both paths call the same `<name>-core` functions. Nothing here needs Tauri's builder to run for the CLI path, so no window is created in that mode. The trade-off from the decision table still applies: the compiled binary includes Tauri regardless of which path executes, and nothing but code review stops CLI code from accidentally reaching into `commands/` or GUI-only state.

---

### C. The Engine — variant: two separate binaries

Business logic entirely in Rust, organized into several crates, consumed by genuinely separate binaries. Same top-level layout as A and B; what is added is a second app under `apps/` and, on evidence, a split of the core crate. Only reach for it when the two-separate-binaries choice was made deliberately (see the decision table in `SKILL.md`), not merely because a CLI was wanted at all.

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
│   ├── <name>-core/              # types, errors, traits, config — profile B's core crate
│   ├── domain/                   # pure business rules, split out on evidence
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
- Only create a crate beyond `<name>-core` when a module exceeds ~500 lines **and** has a stable boundary. A set of 200-line crates degrades build times and creates circular dependency pain while buying nothing.
- `packages/ui/` is only justified with two real frontends. Otherwise it's abstraction debt.
- `apps/cli` (or equivalent) must exist or be planned: without a second consumer, this variant isn't justified. And it must actually be the *two-binaries* choice — if a single dual-mode binary would do, use the lighter §3.B variant above instead.

**Target**: complex software, platforms, multi-frontend apps, reusable engines.

**Second consumer is a server**: when the identified second consumer is a server exposing the same business logic to remote clients (rather than a CLI), swap `apps/cli/` for `apps/server/` (an axum binary, or equivalent), consuming the same crates. This is the standard shape for "desktop app today, multi-client server later" — see §9 for what this migration involves beyond the folder move.

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
- Rust: co-located unit tests (`#[cfg(test)]`) on `domain/`; integration tests in `crates/<name>-core/tests/`.
- `domain/` must be testable **without** a Tauri dependency — guaranteed by the core crate having none. Logic found in `commands/` has leaked there.
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
6. Use the common layout (§3) in every profile: frontend in `apps/desktop/`, root Cargo and npm workspaces. Its configuration (`frontendDist`, `devUrl`, build command cwd) is paid once and copied between projects.
7. `crates/<name>-core` from profile B onward; no further crate, no `packages/` and no second app without an identified second consumer or the §3.C split threshold.
8. Generate nothing tied to a forge or CI system.
9. Document the chosen D1–D7 values in the project `README.md`.
10. **Leave build artifacts where Cargo and Tauri put them.** The other stacks in this portfolio route their output to `dist/release/` and `dist/debug/`; this branch deliberately opts out, for two reasons specific to it:

    - Cargo owns `target/` as an incremental build cache and offers no "final artifact goes here" setting, so the convention would only hold via a post-build copy — extra machinery, a duplicated artifact, and a `cp`/`copy` split to maintain.
    - `dist/` is already taken. Vite's default `build.outDir` is `dist/` (in `apps/desktop/`), so the name would refer to the frontend bundle and to the shipped executable.

    So: `target/release/<name>` for the binary, `target/release/bundle/<format>/` for the installers `tauri build` produces, and `dist/` left to Vite. Say this plainly in the project README, since someone arriving from the Python or Go tools in this portfolio will look for `dist/` first.
11. **Scripts keep the same names in every project**, under `scripts/`, so a colleague moving between apps does not guess:

    | Script | Means |
    |---|---|
    | `dev.ps1` | the desktop dev loop (`tauri dev`), after `clean.ps1` |
    | `check.ps1` | the full gate: fmt, clippy, tests, then the front end's `format:check`, `lint`, `typecheck`, `test`; `-Fast` skips the tests (`references/check.ps1`, copied as-is unless the gate needs more, always with `references/node-env.ps1` beside it as `scripts/node-env.ps1`: the gate dot-sourcing it fails without it) |
    | `build.ps1` | the release build |
    | `package.ps1` | the installer, with hand-out copies if the project ships any |
    | `release.ps1` | publishing what `package.ps1` produced |
    | `clean.ps1` | the `target/` cap (`rust-code-standards` references) |

    Every script that reaches the npm registry, directly or through `tauri`, dot-sources `scripts/node-env.ps1` first: behind a TLS-inspecting proxy Node rejects the corporate root CA and `npm install` fails with `UNABLE_TO_GET_ISSUER_CERT_LOCALLY`. The helper adds `--use-system-ca` to `NODE_OPTIONS` (TLS verification stays on) and does nothing on a Node without the flag.

    Other scripts are fine (`dev-web.ps1`, `sign.ps1`...); these six names always mean the same thing, and the first five match the Wails and Python branches'. The npm scripts `dev` and `build` stay the frontend's own (Vite), not the app's.
12. **One dev port per app.** Pick a port no other app of the portfolio uses, set it in `vite.config.ts` with `server.strictPort: true` and in `devUrl`, and record it in the README. Without `strictPort`, Vite moves to the next free port while `devUrl` still names the old one, so two apps running side by side can show each other's dev server.
13. **`@tauri-apps/api` and `@tauri-apps/cli` track the minor of the `tauri` crate** (`^2.12.3` with `tauri = "2.12.3"`). The CLI warns, and some APIs fail, when the npm and Rust minors drift apart.

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

1. Start with **B**: `domain/` in `crates/<name>-core`, separated from `commands/`, with no Tauri dependency (the crate has none).
2. Keep logic in React as long as it's purely UI-related.
3. Put every authoritative business rule in `domain/`, even when the code is short.
4. Add a second app (`apps/cli`, `apps/server`) when a second consumer exists; it depends on the core crate as the desktop app does.
5. Split the core crate module by module, only past the §3.C threshold — the operation is mechanical **if** step 1 was respected, expensive otherwise.

Don't move to C without a real second consumer: further crates and apps are not amortized by a single frontend.

**A project still on the older layout** (frontend at the root, logic in `src-tauri/src/domain/`): moving to the common layout is a mechanical change — `git mv` of the frontend into `apps/desktop/`, `src-tauri/src/{domain,infra,db}` into `crates/<name>-core/src/`, a root workspace, then fixing paths in `tauri.conf.json` and the scripts. Do it in its own branch, one commit per move, before any behaviour change.

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
This project has several crates and/or packages/.
Per §2 and §3.C, is this profile justified? Check: real second consumer?
crates beyond <name>-core above the split threshold? packages/ with ≥ 2 consumers?
If not justified, propose a simplification plan toward profile B
(one core crate, apps/desktop, root workspace).
```

**Moving from B to C**
```
Assess splitting crates/<name>-core (or, on the older layout, extracting
src-tauri/src/domain/) per §7.
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
