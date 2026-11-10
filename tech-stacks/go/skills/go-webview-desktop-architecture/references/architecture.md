# Reference — Wails 3 Project Architecture (Go + React)

Selection grid, target folder structures, and audit checklist for the Go + Wails branch.
Covers Wails 3 only. Forge-neutral. No CI considerations.

**Contents**
1. The decisions that matter (W1–W6)
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

| # | Decision | Options | Impact |
|---|---|---|---|
| W1 | Where does business logic live? | React / split / Go | Determines the profile |
| W2 | Shape of the service surface | thin service methods / use-case-oriented / broad convenience registration | Very expensive to change later, and doubles as the de facto security boundary (no capability system exists) |
| W3 | Go-side state | stateless / struct fields with `sync.Mutex` or `sync.RWMutex` / one owning goroutine with channels | Testability and race conditions |
| W4 | Error boundary | internal `error` passed through / one typed error returned as `error` | Whether the frontend can react precisely, and what it gets to see |
| W5 | Long-running / progress | blocking service calls / registered typed events, with cancellation | UX on heavy tasks |
| W6 | Frontend location | `frontend/` (Wails default) | No configuration cost — it's what the tool generates |

**W2 is the structuring decision** — the one the others follow from, and it carries extra weight here because it's also the only thing standing in for a permissions model.

---

## 2. Choosing a profile

| Criterion | A. The Storefront | B. The Workshop | C. The Engine |
|---|---|---|---|
| Business logic | React | React (workflow) + Go (system) | Go |
| System access | Low or none | Frequent | Central |
| Reuse outside desktop | No | Rare | Explicit goal, including a server exposing the logic to remote clients |
| Team size | 1–3, front only | Small mixed team | Dedicated Go skills |
| Maturity | Prototype / MVP | Growing product | Platform / engine |
| Tooling complexity | Low | Moderate | Moderate (Go's tooling is lighter than Cargo workspaces) |
| Mobile targets (experimental upstream) | Unlikely | Possible | Possible |

**The metaphors** — use these when explaining to someone unfamiliar with the stack:

- **The Storefront**: you look through it; nothing is made on site. Everything comes from elsewhere.
- **The Workshop**: someone works at a bench with the machine's tools.
- **The Engine**: self-contained mechanics that can power several vehicles; the screen is just a dashboard.

### Decision rules

- **Default: B (The Workshop).**
- **A** only if the app is an interface over a remote API with no significant system access.
- **C** only with a real, identified second consumer (CLI, server, another frontend). Not "just in case".

**What is not a second consumer.** Wails 3 builds the same root package as a GUI-less HTTP server (`-tags server`) and, experimentally, targets iOS and Android. Those are the same application on another surface, produced from the same source by a different build task — they need no extra binary and no extra package layout. Reaching for profile C because "we'll also want the server build" is over-structuring; see §9.

### Out of scope: local HTTP sidecar

A Go process exposing HTTP locally instead of service bindings shows up occasionally (e.g. wrapping a pre-existing HTTP backend). It's rare enough, and different enough in its concerns — port management, process lifecycle, packaging — that it isn't documented here as a profile. Treat it as a one-off design problem if it comes up, not a template to reach for. Before reaching for one, check the two built-in answers: `ServiceOptions.Route` mounts a service implementing `http.Handler` on the app's own asset server, and §9's server build reaches the app over HTTP.

---

## 3. Profiles and folder structures

All three start from what `wails3 init -n <name> -t react -mod <module path>` actually generates (`react` is the TypeScript template; `react-js` is the one to avoid). **There is no `wails.json` in Wails 3** — project configuration lives in `build/config.yml`, and the build is a set of Taskfiles you own.

### Common layout (every profile)

```text
my-app/
├── frontend/
│   ├── src/
│   ├── bindings/                 # generated, committed, included by tsconfig.json
│   ├── index.html
│   ├── vite.config.ts            # server.port = this app's port, strictPort: true
│   └── package.json              # format, format:check, lint, typecheck, test
├── build/                        # generated, load-bearing; customize, don't rewrite (windows/info.json FileDescription = app name, shown by Task Manager)
├── internal/                     # profiles B and C only
├── scripts/                      # §5, rule 13
├── <name>service.go
├── main.go
├── Taskfile.yml
├── go.mod                        # one module
├── go.sum
├── .env.example
└── README.md
```

Configuration this costs once, the same in every project:

- `go.mod`: `toolchain` pinned, `ignore ./frontend/node_modules` and `ignore ./build` (`go-code-standards`, `build-and-disk.md`).- `Taskfile.yml`: `BIN_DIR` per §5 rule 12; `vite.config.ts`, the `-port` in `scripts/dev.ps1` and the `VITE_PORT` default per rule 14.
- No root `package.json`: there is one front-end package, so the gate calls `npm --prefix frontend`.

### A. The Storefront

Go limited to bootstrapping and window setup.

```text
my-app/
├── frontend/                     # React app (Wails default location)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/                  # remote HTTP calls, not Wails bindings
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── bindings/                 # generated — see §4, W2
│   ├── package.json
│   ├── index.html
│   └── vite.config.ts
│
├── build/                        # per-platform build assets and Taskfiles
│   ├── config.yml                # product info, dev-mode config
│   ├── Taskfile.yml              # shared tasks (frontend build, bindings, icons)
│   ├── windows/  darwin/  linux/ # one Taskfile + assets per target
│   └── appicon.png
│
├── <name>service.go              # the one service, thin
├── main.go                       # application.New(...), Services, window, bootstrap only
├── Taskfile.yml                  # root tasks; BIN_DIR and APP_NAME live here
├── go.mod
└── README.md
```

**Target**: MVP, dashboard, REST client, simple tool.

**Constraints**:
- `main.go` stays bootstrap only.
- Create `internal/domain` the day Go holds logic beyond bootstrapping — that is the moment the app becomes a Workshop.

---

### B. The Workshop (recommended default)

```text
my-app/
├── frontend/                     # React app (Wails default location)
│   ├── src/
│   │   ├── components/           # pure presentation, no bindings calls
│   │   ├── features/
│   │   │   └── <feature>/
│   │   │       ├── components/
│   │   │       ├── hooks/
│   │   │       └── index.ts
│   │   ├── pages/
│   │   ├── ipc/                  # THE ONLY place generated bindings are called
│   │   │   ├── client.ts         # wraps generated calls, maps typed errors
│   │   │   └── <domain>.ts
│   │   ├── store/
│   │   ├── lib/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── bindings/                 # generated by `wails3 generate bindings` — do not edit
│   ├── package.json
│   └── vite.config.ts
│
├── internal/                     # Go-enforced private packages, not importable outside the module
│   ├── domain/                   # business logic, no Wails imports, testable standalone
│   │   └── <domain>/
│   ├── infra/                    # adapters: fs, git, process, http, db + migrations
│   ├── state/                    # shared state + locking policy
│   └── apperror/                 # the typed error every service method returns (W4)
│
├── build/                        # as above — generated, load-bearing, don't rebuild by hand
├── scripts/
├── <domain>service.go            # service(s) — thin exposure, calls internal/domain
├── main.go                       # bootstrap only
├── Taskfile.yml
├── go.mod
└── README.md
```

**Split of responsibilities**:

| React | Go |
|---|---|
| UI, navigation, forms, screen state | Files, Git, processes, low-level networking |
| User journey orchestration | Persistence, migrations |
| Display validation | Authoritative business validation |
| — | CPU-bound processing |

**`domain` vs `infra`**: this split makes explicit what is testable without I/O (`domain`) and what touches the outside world (`infra`). It replaces a generic `services` package, ambiguous here since "service" already means the Wails boundary.

**What `internal/` guarantees, and what it doesn't**: the compiler enforces that `internal/` packages are only importable from within the same module tree. It says nothing about what they import, so it does not keep Wails out of `internal/domain`. That half is checked by the gate (`scripts/check.ps1`, through `go list -deps`), which also catches a transitive leak through `infra` — a dependency anti-pattern 10 would otherwise find only in review.

**Service files sit at the root, in `package main`**, as the template generates them. They are thin enough that a package of their own buys nothing; a service can live in its own package if it genuinely grows, since `application.NewService` takes any struct pointer.

**Target**: IDEs, developer tooling, document management, classic desktop apps.

---

### B — variant: CLI access without a second binary

When a CLI companion is wanted but the single-binary, dual-mode option was chosen (see the decision table in `SKILL.md`), this stays entirely inside profile B's shape. Only `main.go` changes:

```go
// main.go
func main() {
    if len(os.Args) > 1 {
        cli.Run(os.Args[1:])   // CLI mode — never builds the application
        return
    }
    app := application.New(application.Options{ /* ... */ })
    // ... window setup ...
    if err := app.Run(); err != nil {
        log.Fatal(err)
    }
}
```

Both paths call the same `internal/domain` functions. The CLI path never constructs the application, so no window is created in that mode. The trade-off from the decision table still applies: the compiled binary includes Wails regardless of which path executes, and nothing but code review stops CLI code from reaching into service types or GUI-only state.

---

### C. The Engine — variant: two separate binaries

Business logic in Go, organized so a second, genuinely separate binary (CLI, server) can use it without going through Wails at all. This is the heavier structure — only reach for it when the two-separate-binaries choice was made deliberately, not merely because a CLI was wanted at all.

```text
my-app/
├── frontend/                      # unchanged — the desktop app stays at the root
├── build/
├── <domain>service.go
├── main.go                        # desktop binary, still the root main package
├── Taskfile.yml
│
├── cmd/
│   └── cli/
│       └── main.go                # 2nd binary — has no Wails dependency at all
│
├── internal/
│   ├── core/                      # types, errors, config
│   ├── domain/                    # pure business rules
│   └── <capability>/              # git, filesystem... on evidence
│
├── go.mod                          # single module — keeps internal/ visibility simple
└── README.md
```

**Why the desktop app stays at the root rather than moving to `cmd/desktop/`**, which is what Go's own multi-binary convention would suggest: the generated build tasks run `go build` in the project root with no package path, and `main.go` embeds the frontend with `//go:embed all:frontend/dist`, a path resolved relative to the file that declares it. Moving the desktop main package under `cmd/` therefore breaks the embed and requires editing the build task in every per-platform Taskfile. The tool's layout wins here, for the same reason W6 leaves `frontend/` alone. Only the second binary, which the toolchain knows nothing about, goes under `cmd/`.

**Constraints**:
- Only create a package beyond `domain` and `infra` when a module exceeds ~500 lines **and** has a stable boundary. A set of tiny packages creates import-cycle pain while buying nothing.
- `cmd/cli` (or equivalent) must exist or be planned: without a second consumer, this variant isn't justified. And it must actually be the *two-binaries* choice — if a single dual-mode binary would do, use the lighter §3.B variant above instead.

**Constraint on Go modules**: keep this as a **single Go module** (one `go.mod` at the root). This keeps `internal/` visibility working without extra ceremony. Only split into multiple modules via a `go.work` workspace if independent versioning or release cadence between the binaries is a real requirement — not by default.

**Second consumer is a server**: before adding `cmd/server/`, check whether the built-in server target already covers the need — see §9. It does not when the server must serve *several* clients with distinct data; it does when the goal is the same single application reachable over HTTP.

**Target**: complex software, platforms, multi-frontend apps.

---

## 4. Cross-cutting decisions in detail

### W2 — Shape of the service surface
A service is an ordinary Go struct registered on the application:

```go
app := application.New(application.Options{
    Services: []application.Service{
        application.NewService(&ProjectService{}),
    },
})
```

Its **exported** methods are what the frontend can call; unexported ones are unreachable. A service method should: receive the call, invoke `internal/domain`, map any error into the typed result, return. If a service's methods mirror `internal/domain` function-for-function, the layer adds nothing.

A service that holds resources implements `ServiceStartup(ctx, options)` and `ServiceShutdown()`. They run in registration order and in reverse, and a startup error stops the application. Put opening the database there, not in `init()` or in the constructor.

Granularity: prefer **use-case-oriented** methods (`OpenProject`) over **technical CRUD** (`ReadFile`, `ParseConfig`, `ValidateConfig`). This matters more in Wails than in Tauri, because every exported method is also a permission grant — there's no separate manifest to narrow later. Capitalization is part of the security design here, not just style.

Bindings are generated into `frontend/bindings/`, organized by package and service, by `wails3 generate bindings` — which the build tasks invoke, so it also runs under `wails3 dev`. Never hand-edit that directory.

### W3 — Go-side state
- Stateless wherever possible.
- Struct fields on the service type for simple shared state; guard with `sync.Mutex` or `sync.RWMutex` when accessed from multiple goroutines (service methods and background goroutines can run concurrently).
- For anything with multiple interdependent pieces of state, prefer a single goroutine owning the state and communicating via channels — Go's idiomatic actor shape — over multiple mutexes, beyond 2–3 of them.
- Never hold a lock across a blocking call (I/O, a channel operation, a service or event round trip): it is Go's form of Rust's lock-across-`.await`.

### W4 — Error boundary
A failed service call rejects the frontend's promise with a `RuntimeError` carrying two things: `message`, the Go error's `Error()` text, and `cause`, the error serialized with `encoding/json`. That sets both of the traps:

- `errors.New` and `fmt.Errorf` values have no exported fields, so `cause` is `{}`: nothing to branch on.
- `message` is always the raw text, so `fmt.Errorf("reading %s: %w", path, err)` hands the frontend an absolute path.

So every service method returns one typed error, and never passes an internal one through:

```go
// internal/apperror
type AppError struct {
    Code    string `json:"code"`    // stable discriminant, e.g. "FILE_NOT_FOUND"
    Message string `json:"message"` // safe to display, no internal details
}

func (e *AppError) Error() string { return e.Message }
```

```ts
// frontend/src/ipc/client.ts: the one place that reads it
import { Call, CancelError } from "@wailsio/runtime";

// error instanceof CancelError       → this side called .cancel(): not a failure (W5)
// error instanceof Call.RuntimeError → the Go method failed: switch on error.cause.code
// anything else (TypeError, Error)   → the call itself failed: a bug, not a user-facing case
```

Log the internal detail on the Go side (structured logging) before mapping it. A panic in a service method is recovered into a `RuntimeError` as well, with no `cause` and with its text as the message (`main.ProjectService.Boom: panic: boom`), so `ipc/client.ts` must treat a missing `code` as a generic failure and show none of that `message`. `ServiceOptions.MarshalError` and its `Options`-level twin change only `cause`, so they can't fix a leaking `message`: mapping stays the service's job.

Don't wrap results in a `Result[T]` struct, a habit from before the runtime exposed `cause`: every call would then resolve as a success, and `ipc/` would have to rebuild rejection by hand.

### W5 — Long-running work
Register the event type at startup so the binding generator produces a typed API for it, then emit from anywhere:

```go
application.RegisterEvent[ProgressPayload]("import:progress")   // in init() or main()
app.Event.Emit("import:progress", ProgressPayload{Done: 42})
```

Events are broadcast-shaped: any listener receives any emitted event. For per-call progress where only the calling component should react, carry a request ID in the payload (or in the event name) and filter client-side.

Calls are short request/response; anything over ~500 ms reports progress. To make it cancellable, take `context.Context` as the method's first parameter: the binding generator leaves it out of the JS signature, the generated call returns a `CancellablePromise`, and its `.cancel()` cancels that context. Pass it down into `internal/domain`, and check it in the loop. The promise rejects at once with a `CancelError`, not a `RuntimeError`, and whatever the Go method returns afterwards never reaches the frontend: don't return a "cancelled" value for the UI to read.

### W6 — Frontend location
`wails3 init` scaffolds `frontend/` as a subfolder with the Go files at the root, and `main.go` embeds `frontend/dist`. Don't fight this default; there's no configuration cost either way since it's what the tool already does. Note this makes `frontend/dist` Vite's output — the frontend bundle, not the shipped binary.

### Security — no capability system
Restated because it's easy to underweight: everything exported on a registered service is fully privileged. The practical mitigation is treating the `Services:` list plus method capitalization as the permission boundary — review them the way you'd review a Tauri capabilities file, even though no such file exists here.

### Secrets and configuration
Anything prefixed `VITE_` is in plain text in the bundle, and so is anything else under `frontend/dist`, which is embedded in the binary as it stands: never a secret. API keys live on the Go side and are not returned through a service method. Version `.env.example`, gitignore `.env`.

### Testing
- Go: standard `_test.go` files co-located with `internal/domain`; that package must build and test without importing any Wails package.
- Frontend: same as the shared React reference — vitest, `ipc/` mocked at its module boundary.
- End to end, when a project needs it: upstream's route is Playwright against the server build (§9), which runs the real services in a browser. Vite's dev server alone provides no bindings.

---

## 4b. Where the app writes at runtime

Distinct from where the code lives: where the installed application writes
settings, its database, and its logs. Writing beside the executable works
throughout development and breaks the day the app is installed under
`Program Files`, where the process has no write access — so it surfaces at the
user's site, not on the developer's machine.

Resolve the paths from `os.UserConfigDir()` for settings and state, and
`os.UserCacheDir()` for anything regenerable, joined with an app-specific
subfolder. Logs are not regenerable and go under the config directory. Resolve them once at startup and pass them into `internal/domain` —
domain code should receive a path, never derive one from `os.Executable()`,
which is what couples it to the desktop binary and breaks the moment
`cmd/cli/` or the server build reuses it.

---

## 5. Scaffolding rules

1. Determine the profile via §2. Ask if information is insufficient.
2. **Scaffold with `wails3 init -n <name> -t react -mod <module path>`**, then reshape. The `build/` tree, its per-platform Taskfiles and `build/config.yml` are load-bearing and version-specific — don't write them from memory. The module path is not a detail to fix later: the default, `changeme`, has no dot, so gofumpt reads it as standard library and `golangci-lint fmt --diff` never passes, and the bindings' folder follows it (`frontend/bindings/github.com/acme/app/`), so renaming breaks every generated import.
3. Only create folders actually used.
4. Keep service methods thin; all setup logic in `main.go`, all business logic in `internal/domain`.
5. Create the shared error type (`internal/apperror` or similar) from profile B onward, even minimal.
6. Review the exported surface explicitly — don't register a service "for convenience" that exposes more than the app needs, and don't export a method the frontend never calls.
7. Leave `frontend/` where `wails3 init` puts it (§ W6) — no reason to move it.
8. Don't create a multi-binary or multi-module layout without an identified second consumer, and don't count the server or mobile targets as one (§2).
9. Generate nothing tied to a forge or CI system.
10. Document W1–W6 in the project README.
11. **Pin Wails, and move the three versions together.** The `github.com/wailsapp/wails/v3` line in `go.mod`, `@wailsio/runtime` in `frontend/package.json` (exact, as the template writes it) and the `wails3` CLI (`go install github.com/wailsapp/wails/v3/cmd/wails3@<version>`) are one version, with no `^`. Upstream ships a feature release every week and a nightly most days: upgrade deliberately, in its own commit, read the release notes, then `wails3 task common:update:build-assets` and review what it overwrote. Never depend on a nightly tag.
12. **Route final build artifacts to `dist/`** at the repository root — `dist/release/` and `dist/debug/`, gitignored (add `/dist`; the template only ignores `bin` and `frontend/dist`). This is a one-variable change plus the dev loop: the root `Taskfile.yml` declares `BIN_DIR`, which every platform task uses for the binary and for `run`, and `wails3 dev` runs a `DEV=true` build, so without the second edit it overwrites the release binary.

    ```yaml
    # Taskfile.yml
    vars:
      APP_NAME: "myapp"
      BIN_DIR: "dist/release"
    ```

    ```yaml
    # build/config.yml, dev_mode.executes: only these two commands change
    - cmd: wails3 build DEV=true BIN_DIR=dist/debug
      type: blocking
    - cmd: wails3 task run BIN_DIR=dist/debug
      type: primary
      exit_policy: shutdown
    ```

    ```bash
    # release
    wails3 build
    # debug — DEV=true keeps inlining and skips stripping; override the output dir
    wails3 build DEV=true BIN_DIR=dist/debug
    # the CLI binary, if profile C
    go build -o dist/release/<name> ./cmd/cli
    ```

    The NSIS task works in `build/windows/nsis/` and reads the binary from `BIN_DIR`; MSIX writes beside the binary. `frontend/dist` is Vite's output and is unrelated — it gets embedded into the binary rather than shipped. The Python stack in this portfolio uses the same `dist/release` + `dist/debug` destination; the Tauri branch deliberately opts out and keeps Cargo's `target/` layout, for reasons given in that skill's reference.
13. **Scripts keep the same names in every project**, under `scripts/`, so a colleague moving between apps does not guess:

    | Script | Means |
    |---|---|
    | `dev.ps1` | the desktop dev loop (`wails3 dev -port <n>`) |
    | `check.ps1` | the full gate: `golangci-lint fmt --diff`, `golangci-lint run`, `go test`, `internal/domain` free of Wails, regenerated bindings, then the front end's `format:check`, `lint`, `typecheck`, `test`; `-Fast` skips the tests, not the bindings: the typecheck reads them (`references/check.ps1`, copied as-is unless the gate needs more) |
    | `build.ps1` | the release build (`wails3 build`) |
    | `package.ps1` | the installer (`wails3 package`), with hand-out copies if the project ships any |
    | `release.ps1` | publishing what `package.ps1` produced |

    Other scripts are fine (`dev-feedback.ps1`, `sign.ps1`...); these names always mean the same thing, and match the Tauri and Python branches'. Tauri has a sixth, `clean.ps1`, which has no equivalent here because Go's cache caps itself (`build-and-disk.md`). The npm scripts `dev`, `build` and `build:dev` stay the frontend's own (Vite), and the build tasks call them by those names.
14. **One dev port per app.** Pick a port no other app of the portfolio uses instead of the template's `9245`: pass it as `wails3 dev -port <n>` in `scripts/dev.ps1`, change `VITE_PORT`'s default in `Taskfile.yml` and the fallback in `vite.config.ts` to match, and record it in the README. The template sets `strictPort: true`, so two apps on one port fail at startup rather than show each other's dev server — keep it.
15. **`go.mod` gets `ignore ./frontend/node_modules` and `ignore ./build`.** npm packages and the template's mobile targets both ship Go source, and without these lines `go test ./...` and `golangci-lint` take them as part of the module (`build-and-disk.md`).
16. **`frontend/dist` is gitignored and embedded**, so on a fresh clone `go test` and `golangci-lint` fail with `pattern all:frontend/dist: no matching files found`. `scripts/check.ps1` creates a placeholder; a CI job that doesn't run it needs to do the same or build the front end first. `wails3 build` also runs `go mod tidy`, so read any `go.mod` change a build leaves behind before committing it.
17. **`frontend/bindings/` is committed**, as the template's `.gitignore` leaves it: `tsc` reads it, and a signature change shows up in the diff of the commit that made it.
18. **The per-user NSIS installer takes two includes from `references/nsis/`**, and `project.nsi` there is a ready-made script that uses them**, which assume `!define WAILS_INSTALL_SCOPE "user"` in `project.nsi` (the template's default is machine-wide: admin, `HKLM`, `Program Files` — none of the includes' registry or folder checks would match), copied to `build/windows/nsis/` and `!include`d from the template's `project.nsi`; both need the `INFO_*`, `UNINST_KEY` and `PRODUCT_EXECUTABLE` defines `wails_info.nsh` / `wails_tools.nsh` already provide.
    - `path.nsh` — an optional, ticked-by-default component that **appends** the install folder to the user `PATH` and removes only that entry on uninstall. It never rewrites what it cannot read back intact: a `PATH` of 1000+ characters (NSIS strings stop at 1023 and `ReadRegStr` truncates silently) is left alone and the user is told in a dialog. Wire it as `Section "Add to the PATH (current user)" SecPath` calling `AppPathAdd`, and `un.AppPathRemove` in the uninstall section.
    - `upgrade.nsh` — updating by running a newer installer: reuse the installed folder, refuse a downgrade (exit code 2), wait for the app and an optional second executable (`!define APP_EXTRA_EXE "tool.exe"` before the include) to be closed (silent: exit code 5). Call `AppCheckInstalled` from `.onInit`, `AppWaitForExit` first in the install section, and write `InstallLocation` into `${UNINST_KEY}` next to the uninstaller (`SetRegView 64`).
    - `project.nsi` — a complete per-user `project.nsi` to start from instead of the template's: it wires `upgrade.nsh` (and `un.AppWaitForExit` in the uninstaller), reads the French/English system language, offers a desktop shortcut whose choice survives updates, a "Launch" box on the last page, and **uninstalls only the files it wrote** (`Delete` + a non-recursive `RMDir`, never `RMDir /r $INSTDIR`: the user may have picked Documents). Settings and the WebView2 profile (`%AppData%\<exe name>`, go-webview2's default) are deleted only after a Yes in a dialog, never in silent mode. Keep it saved as UTF-8 **with BOM** (Unicode installer: no BOM means ANSI, accents garbled). `wails3 package` already passes `-DWAILS_INSTALL_SCOPE=user`, so the `!define` must stay behind `!ifndef`. Translate `upgrade.nsh` by defining the `APP_MSG_*` it lists before the include.
    - `makensis` without admin rights: the NSIS zip, unpacked into the user profile — `references/nsis/install-nsis.md`.
    - Test registry code against a scratch key (`!define APP_ENV_KEY "Software\<co>\Scratch"` before the include), never the real `HKCU\Environment`.

---

## 6. Anti-patterns — audit checklist

| # | Symptom | Diagnosis |
|---|---|---|
| 1 | A component imports from `frontend/bindings/` directly | No `ipc/` layer — see shared React reference §2 |
| 2 | Service methods mirror `internal/domain` 1:1 | Layer with no added value |
| 3 | Business logic inside a service method's body | `internal/domain` not testable without Wails |
| 4 | An internal or wrapped `error` returned from a service method, or a `Result[T]` wrapper | Frontend can't react precisely, and `message` leaks paths and internals (W4) |
| 5 | A service registered "for convenience" exposing unrelated methods, or methods exported that nothing calls | No manifest to catch this later — it's the permission surface, treat it as one |
| 6 | Many small Go packages under `internal/` with circular imports | Premature split |
| 7 | Blocking service call > 1 s with no progress event | Frozen UX, no cancellation (W5) |
| 8 | Shared state mutated from a goroutine without a mutex, or a lock held across a blocking call | Race condition or deadlock (W3) |
| 9 | Business logic duplicated in React and Go | W2 boundary never settled |
| 10 | `internal/domain` depending on any `wails/v3` package, directly or through `infra` | Coupled to Wails, can't be reused by `cmd/cli` or tested standalone; the gate fails on it |
| 11 | Multiple Go modules (`go.work`) with no independent-release justification | Unnecessary tooling complexity |
| 12 | Hand-written TS types duplicating what `wails3 generate bindings` produces | Redundant, will drift |
| 13 | Missing or manual DB migrations | Non-reproducible schema |
| 14 | Frontend moved out of `frontend/`, or the desktop main package moved under `cmd/` | Fighting the tool's default; breaks the embed and every platform build task (§3.C) |
| 15 | No test exercising `internal/domain` without constructing the application | Signals logic and Wails runtime were never actually separated |
| 16 | `build/` Taskfiles hand-rewritten rather than customized | They're regenerated assets; changes are lost and version drift becomes invisible. Editing a metadata value in place is customizing, not rewriting: `wails3 init` fills `build/windows/info.json` `FileDescription` with the app's tagline, which Windows Task Manager shows as the process name, so set it to the app name |
| 17 | Writes configuration, database or logs beside the executable | Breaks on any read-only or per-machine install; surfaces only after deployment (§4b) |
| 18 | Multi-binary layout justified by the server or mobile build target | Those come from the same root package; no second consumer exists (§2, §9) |
| 19 | Secrets reachable from the frontend: `VITE_` values, files in `frontend/dist`, a service method returning a key | Leak in the bundle or through the permission surface |
| 20 | `go.mod`, `@wailsio/runtime` and the CLI on different versions, or a nightly tag | Bindings and runtime disagree; failures that look like application bugs (§5, rule 11) |
| 21 | No `ignore ./frontend/node_modules` or `ignore ./build` in `go.mod` | `./...` takes in Go files from npm packages and generated mobile sources (§5, rule 15) |
| 22 | The `mcp` build tag, or `WAILS_MCP=1`, in a release build or script, or `--remote-debugging-port` in a file without `//go:build !production` | Ships a local control channel into the app |
| 23 | Wake, purego or a mobile target adopted with no recorded decision | Experimental upstream, outside the stable compatibility contract |
| 24 | Long-running service method with no `context.Context` first parameter | The frontend's `.cancel()` has nothing to act on (W5) |

**Reporting priority**: leaky boundaries (1, 2, 3, 9) and the exposed surface (5, 19) before naming or layout issues — those are the ones that compound over time.

---

## 7. Evolution path

One caution up front: **there is no easy migration from B to C.** What changes is the shape of the boundary, not where the code sits.

1. Start with **B**, `internal/domain` already free of Wails imports.
2. Keep logic in React while it's purely UI-related.
3. Put every authoritative business rule in `internal/domain`.
4. Add `cmd/<name>/` only once an `internal/domain` module has a stable boundary **and** a second consumer exists.
5. Keep it a single Go module unless independent versioning is a real need (§3.C).

Don't move to C without a real second consumer: further binaries and packages are not amortized by a single frontend.
---

## 8. Prompts (standalone use)

Useful if this file is provided on its own, without the skill.

**New project, profile to determine**
```
Project: <2-3 sentence description>
Expected system access: <files / git / processes / DB / none>
Team: <size, Go experience or not>
Planned other consumer of the business logic: <yes/no, which>

Step 1: recommend a profile (A/B/C) with justification, and propose values
for W1–W6. Create no files.
Step 2: after approval, scaffold with `wails3 init -n <name> -t react -mod <module path>` and reshape it
per §5, then read react-conventions.md for the frontend side.
```

**Full audit**
```
Audit this Wails 3 project:
1. Confirm it is v3 (Services: in main.go). If it's v2, stop and say so: this
   reference doesn't apply.
2. Identify the actual profile and the gap with the appropriate one.
3. Walk the §6 checklist point by point, with files and lines as evidence.
4. Review the Services: list and every exported method on those services as a
   permission-surface question — is each one something the app actually needs
   client-accessible?
5. Assess W1–W6 as currently implemented.
6. Rank issues by increasing cost to fix.
Modify no files.
```

**Service surface review**
```
List every service registered in application.Options{Services: ...} and every
exported method on those types. For each, state what it allows the frontend to
do, and whether that's the minimum necessary surface. Flag anything registered
"for convenience", and any exported method the frontend never calls.
```

**Targeted audit of the boundary**
```
Per §4 (W2, W4) and §6, analyze the service boundary:
- do service methods contain business logic?
- are they use-case oriented or technical CRUD?
- has business orchestration leaked into React?
- does every method return the typed error, or can an internal message reach the
  frontend?
- does `go list -deps ./internal/domain/...` show any Wails package?
Give a verdict per method and an ordered remediation plan.
```

**Profile justification check**
```
This project has a cmd/ directory, several internal packages and/or a go.work.
Per §2 and §3.C, is this profile justified? Check: real second consumer, and not
the server or mobile target? packages above the split threshold? independent
release cadence for a second module?
If not justified, propose a simplification plan toward profile B.
```

**Moving from B to C**
```
Assess extracting internal/domain into a shape usable by a second consumer
(cmd/cli or cmd/server) per §7. First: is this a real second consumer, or is it
the built-in server/mobile target (§2, §9)? Then check the prerequisite: is
internal/domain free of Wails imports? If not, list what to break first. If yes,
propose the cmd/ layout and justify keeping a single Go module vs go.work.
```

**Evolving toward a server with remote clients**
```
Assess exposing this app's business logic to remote clients via a server, per §9.
Cover:
1. Whether the built-in server build is enough, or several clients with distinct
   data need a real server.
2. Which internal/domain modules are centralizable vs inherently local
   (filesystem, Git, local processes) — classify module by module.
3. Whether the service surface (W2) is use-case oriented and typed enough to
   reuse as the shape of an HTTP API.
4. What's still unaddressed: multi-user authentication, sessions, data isolation
   between clients.
Produce a plan, don't move code yet.
```

---

## 9. Evolving toward a server with remote clients

Wails 3 builds the same root package as a GUI-less HTTP server: `wails3 task build:server` compiles with `-tags server` and produces `<name>-server`, with a Docker target alongside it. That is genuinely useful, and it is also the part most likely to be misread — so be precise about what it gives you.

**What it gives you**: the same application, same services, same frontend, reachable over HTTP instead of drawn in a native window. No second package layout, no extracted crates or modules, no separate consumer. If the goal is "run this tool on a machine and reach it from a browser", this is the whole answer and profile C is unnecessary.

**What it does not give you**, and none of it is covered by W1–W6:

1. **Not everything in `internal/domain` can centralize.** Local file, process and Git access is inherently client-side — on a server it operates on the *server's* machine, which is a different program with different meaning. Classify module by module before assuming a move is mechanical.
2. **Design W2 as if it were already a network API.** Use-case-oriented service methods reuse cleanly as HTTP handlers: a service method and an `http.HandlerFunc` can call the same `internal/domain` function, with only the transport wrapper differing. Sloppy W2 today is a second design pass later.
3. **Multi-user authentication and data isolation remain entirely unaddressed** — and the server target makes this *more* dangerous, not less, because one command turns a single-user desktop application into something reachable over a network while preserving its assumption that whoever is at the keyboard is trusted. There are no users, no sessions, no isolation between clients. That needs its own design pass on the server side, and it should be raised before anyone reads `build:server` as a multi-client architecture. Upstream's deployment advice (bind to localhost, TLS, a reverse proxy, same-origin WebSockets) hardens the transport; it does not answer this.
