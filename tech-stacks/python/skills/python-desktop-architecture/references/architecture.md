# Reference — Python Desktop Architecture (PySide6 / tkinter)

Common layout, folder structures, background-work and error patterns, packaging and protection detail, scaffolding rules, audit checklist.

**Contents**
1. Common layout, and the PySide6 tree
2. Folder structure — tkinter
2b. CLI access and reusable logic
3. Background work in detail
3b. The error boundary
4. Packaging in detail
4b. Where the app writes at runtime
5. Scaffolding rules
6. Protecting sensitive logic in detail
7. Anti-patterns — audit checklist
8. Prompts (standalone use)
9. Evolving toward a server with remote clients

---

## 1. Common layout, and the PySide6 tree

### Common layout (both interface layers, both structural states)

```text
my-app/
├── src/
│   └── <name>/                   # the one package: __main__, ui/, core/, workers/
├── tests/                        # tests core/ directly, no QApplication
├── resources/                    # icons, qss: PySide6 only
├── scripts/                      # §5, rule 11
├── pyproject.toml                # project, dev dependency group, ruff and mypy config
├── uv.lock                       # committed
├── .python-version               # the interpreter, pinned
└── README.md
```

Configuration this costs once, the same in every project:

- `uv init --package <name>` produces the `src/` layout, `.python-version` and a `.gitignore` already covering `dist/` and `.venv`; add `.build/` and `.env`.
- The dev dependency group holds `ruff`, `mypy`, `pytest` and `pyinstaller` (`python-code-standards` for the configuration).
- `scripts/check.ps1` is `references/check.ps1`, copied as-is.

**Why one layout**: scripts, the gate and the docs are copied between projects unchanged, and a colleague moving between apps of the portfolio finds things in the same place. Adding a CLI later is an addition (`src/<name>/cli/`), never a move. This is the `src/` layout uv and PyInstaller work with out of the box; there is no `apps/` folder because, unlike the webview branches, there is no second-language front-end package to give a home.

**What nothing enforces, and what does instead.** Tauri's core crate has no Tauri dependency to reach for, so the compiler keeps the framework out of the logic. Python has no equivalent: `core/` imports PySide6 by an ordinary `import`, and nothing breaks. **The gate supplies the guarantee**: `scripts/check.ps1` imports every module under `core/` (and `cli/`, and any `packages/`), and fails when an interface framework ends up loaded, directly or through another module. It also reads each file for an import placed inside a function, which importing does not run.

### PySide6

```text
my-app/
├── src/
│   └── myapp/
│       ├── __init__.py           # no imports: core/ and cli/ load it too (§5, rule 7)
│       ├── __main__.py           # entry point: QApplication setup only
│       ├── ui/                   # windows, dialogs, widgets — framework code only
│       │   ├── main_window.py
│       │   └── widgets/
│       ├── core/                 # business logic — NO PySide6 imports, testable alone
│       │   ├── __init__.py
│       │   ├── errors.py         # AppError (§3b)
│       │   └── <domain>.py
│       ├── workers/              # background-work wrappers around core/ calls
│       │   └── <task>_worker.py
│       ├── state.py              # explicit app state objects, not globals
│       ├── settings.py           # QSettings wrapper, runtime paths (§4b)
│       └── errors.py             # the exception hooks, AppError → message
├── tests/
│   └── test_<domain>.py          # tests core/ directly, no QApplication needed
├── resources/
│   ├── icons/
│   └── qss/                      # stylesheets, if used
├── scripts/
├── pyproject.toml
├── uv.lock
├── .python-version
└── README.md
```

**The rule that matters**: `core/` must never import `PySide6`. If it does, the logic can't be tested without launching an application, can't be reused if the interface changes, and can't be cleanly compiled on its own later (§6). The gate fails on it.

## 2. Folder structure — tkinter

Same principle, smaller shape. Only for genuinely small tools.

```text
my-app/
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── __main__.py           # Tk() root setup, main loop
│       ├── ui.py                 # widgets — or ui/ package if it grows past one file
│       ├── core/                 # business logic — NO tkinter imports
│       │   ├── errors.py
│       │   └── <domain>.py
│       ├── state.py
│       └── errors.py
├── tests/
├── scripts/
├── pyproject.toml
├── uv.lock
├── .python-version
└── README.md
```

**If this grows past two or three screens, that's the signal to move to PySide6.** Because `core/` has no tkinter imports — which the gate checks just as it does for PySide6 — the move means rewriting the interface only: the logic and its tests carry over unchanged. This is the main practical reason to keep the separation even in a small tool.

## 2b. CLI access and reusable logic

Two separate questions, often confused. A CLI companion is a question of **how many executables** ship, and is answered inside the application-only state. Reusable logic is a question of **who installs `core/`** without the app, and is the second structural state.

### A CLI companion

Two ways to build it — never default, always ask which one fits:

| | Single executable, dual-mode | Two executables, one package |
|---|---|---|
| What ships | One executable — runs as CLI with arguments, opens the window with none | Two executables, built from the same `src/<name>/` |
| CLI weight | Bundles PySide6, imports it only in the window branch | Lean — PyInstaller follows imports, so the CLI build contains no Qt at all |
| Guarantee against interface code leaking into CLI logic | None but discipline | The gate: it checks `cli/` like `core/` |
| Folder shape needed | None beyond §1 — a branch in `__main__.py` | An added `src/<name>/cli/` package, and a second PyInstaller entry |
| Fits best | Simple distribution, occasional CLI use | CLI invoked repeatedly in scripts or CI, where startup time and size matter |

**Single executable, dual-mode** — just a branch in `__main__.py`:

```python
# __main__.py
import sys

def main():
    if len(sys.argv) > 1:
        from myapp.cli import run_cli
        return run_cli(sys.argv[1:])   # CLI mode — PySide6 never imported
    from myapp.ui.main_window import launch
    launch()
```

Importing PySide6 only inside the branch that needs it (rather than at module top level) keeps the CLI path from paying PySide6's import cost even though it's still bundled into the same executable.

**Two executables, one package** — `src/myapp/cli/__main__.py` is the CLI's entry point, built by its own PyInstaller command into the same `dist/release/` (§4). PyInstaller bundles what the entry point imports, so as long as `cli/` reaches only `core/` — what the gate checks — the CLI executable carries no Qt. One `pyproject.toml`, one `uv.lock`, one version.

### Reusable logic: `core/` as a package of its own

Only when something must **install** the logic without the app: a server, a scheduled job on another machine, another team's tool. A CLI shipped next to the app is not that case — see above.

The app stays at the root, which becomes a uv workspace; the core moves to `packages/` and the new consumer is added beside it:

```text
my-app/
├── src/myapp/                     # the desktop app, unchanged except core/ is gone
├── packages/
│   ├── myapp-core/                # workspace member, NO interface imports
│   │   ├── src/myapp_core/
│   │   ├── tests/
│   │   └── pyproject.toml         # its dependencies never list PySide6
│   └── myapp-server/              # the consumer that justified the split
├── tests/
├── scripts/
├── pyproject.toml                 # [tool.uv.workspace] members = ["packages/*"]
├── uv.lock                        # one lockfile, at the root
└── .python-version
```

```toml
# root pyproject.toml
[project]
dependencies = ["myapp-core", "PySide6-Essentials==6.x.y"]

[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
myapp-core = { workspace = true }

[tool.pytest.ini_options]
# Several tests/ folders: without it, two test files with the same name collide.
addopts = "--import-mode=importlib"
```

**What the split does and does not guarantee.** `myapp-core`'s own `pyproject.toml` documents that it needs no interface framework, and a consumer installing it elsewhere gets none. But the workspace shares one `.venv`, where PySide6 *is* installed, so an import from `myapp-core` into the interface still works on the developer's machine. The gate checks every package under `packages/`, which is what turns the declaration into a guarantee.

**Don't reach for this layout early.** Until something genuinely installs the core without the app, it's overhead: one more `pyproject.toml`, a workspace, and a longer path from edit to run.

---

## 3. Background work in detail

One interface thread exists. Blocking it freezes the window. The two frameworks solve this differently.

**PySide6** — a worker object moved onto a background thread, communicating back through signals:

```python
class Worker(QObject):
    progress = Signal(int)
    finished = Signal(object)
    failed = Signal(object)            # an AppError, never str(exc) — §3b

    def __init__(self, params, cancel: threading.Event):
        super().__init__()
        self.params = params
        self.cancel = cancel

    def run(self):
        try:
            result = core.do_the_work(self.params, on_progress=self.progress.emit, cancel=self.cancel)
            self.finished.emit(result)
        except AppError as exc:
            self.failed.emit(exc)
        except Exception:              # worker boundary: nothing may escape the thread
            log.exception("worker failed")
            self.failed.emit(AppError("UNEXPECTED", "The operation failed."))
```

The worker is created, moved onto a `QThread` with `moveToThread`, and its signals connected to interface slots. **Prefer this over subclassing `QThread` and putting logic in `run()`** — a widespread pattern that couples the work to the thread and makes it untestable on its own.

**tkinter** — no signal system, so use a `queue.Queue` and poll it from the main loop:

```python
def poll_queue(self):
    try:
        while True:
            msg = self.queue.get_nowait()
            self.handle(msg)
    except queue.Empty:
        pass
    self.root.after(100, self.poll_queue)
```

The background thread pushes progress, results and `AppError`s onto the queue; only the main loop touches widgets. **Never update a widget from a background thread in tkinter** — it is not thread-safe and the failures are intermittent and hard to diagnose.

**Long work reports progress and can be cancelled.** Anything over ~500 ms reports progress, as above. To make it cancellable, `core/` takes a `threading.Event` (not a Qt type) and checks it in its loop; the interface's Cancel button sets it. The worker then emits nothing further: a cancelled run is not a failure for the interface to display.

## 3b. The error boundary

`str(exc)` is the trap here, the same one the webview branches guard against: an `OSError`'s text carries the full path, a library exception its internals, and none of it gives the interface anything to branch on. So `core/` raises one typed error for every failure it expects:

```python
# core/errors.py
class AppError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code          # stable discriminant, e.g. "FILE_NOT_FOUND"
        self.message = message    # safe to display, no paths, no internals
```

- `core/` catches what it expects (`FileNotFoundError` reading a project) and raises `AppError(...) from err`, which keeps the chain for the log.
- The interface switches on `code` to show the right message; it never displays `str()` of anything else.
- Anything that isn't an `AppError` is a bug: logged with its traceback, shown as a generic failure. The top-level `errors.py` wires the same handling to `sys.excepthook` (and `threading.excepthook` for plain threads), so a crash in a callback leaves a trace instead of vanishing (P6).

---

## 4. Packaging in detail

**Build from a locked environment.** PyInstaller bundles whatever happens to be
installed, so an unlocked environment makes the shipped artifact depend on the
day it was built and on whose machine built it — which is a large share of the
"it works here but not there" reports the rest of this section warns about.
Manage the environment with `uv`, commit `uv.lock`, and build after
`uv sync --locked` (which the gate runs).

### PyInstaller — the default

`scripts/build.ps1` runs these, through `uv run`:

```bash
# release
pyinstaller --onedir --windowed --name myapp \
  --distpath dist/release --workpath .build/pyinstaller --specpath .build \
  src/myapp/__main__.py

# debug — no --windowed, so the console stays visible for print/log output
pyinstaller --onedir --name myapp \
  --distpath dist/debug --workpath .build/pyinstaller --specpath .build \
  src/myapp/__main__.py

# the CLI, when two executables ship (§2b)
pyinstaller --onedir --name myapp-cli \
  --distpath dist/release --workpath .build/pyinstaller --specpath .build \
  src/myapp/cli/__main__.py
```

**`--distpath`**: routes the packaged app to `dist/release/` or `dist/debug/` at the repository root, gitignored — the same destination convention as the Go stack in this portfolio, so "where's the thing I actually ship" doesn't depend on which of those branches a given tool came from. (The Tauri branch deliberately opts out and keeps Cargo's `target/` layout — see that skill's reference for why.) `--workpath` and `--specpath` keep PyInstaller's intermediate files and its generated `.spec` in `.build/` rather than the default `build/` and the root. Dropping `--windowed` for the debug build is a deliberate, meaningful difference: it keeps the console attached so print statements and unhandled exceptions are visible during development testing.

- `--onedir` produces a folder. Starts noticeably faster than `--onefile`, which unpacks itself to a temporary directory on **every** launch.
- `--windowed` suppresses the console window on Windows and macOS.
- Use `--onefile` only when single-file distribution is a hard requirement, and expect the startup cost.

When the command line outgrows itself (hidden imports, data files), commit a `.spec` file and point `build.ps1` at it instead; the destinations stay the same.

**Size: depend on `PySide6-Essentials`**, not the `PySide6` meta-package, unless the app uses an Addons module (WebEngine, Charts, 3D, Multimedia...). The meta-package pulls in Addons, and PyInstaller can't always tell which of their plugins and libraries are unused.

**Qt plugin issues with PySide6**: PyInstaller has a documented history of not copying Qt's platform plugins correctly, producing a runtime failure along the lines of "no Qt platform plugin could be initialized" — typically on a machine other than the developer's. Always test the built application on a clean machine, not just the build machine. If plugins are missing, Qt's own `windeployqt` tool can be run against the output folder to complete the deployment.

**Antivirus false positives**: a well-documented, ongoing problem rather than an occasional glitch. Windows Defender, SmartScreen and various endpoint tools flag PyInstaller output because bundling an interpreter and self-extracting at startup matches the behavioural signature of packed malware. The PyInstaller team updates its bootloader periodically, which helps but never fully resolves it.

What actually reduces it:
1. Use the latest stable PyInstaller.
2. Prefer `--onedir` (the compression in `--onefile` is a common trigger).
3. **Sign the executable.** Code signing does not protect your source, but it establishes publisher identity and resolves most SmartScreen warnings. For anything distributed outside the organisation, treat this as required rather than optional.

### Nuitka — when startup and speed matter

```bash
nuitka --standalone --enable-plugin=pyside6 --follow-imports src/myapp/__main__.py
```

Compiles the whole application to a native binary: faster startup, faster execution, no interpreter bundled visibly. Costs longer build times and occasional friction with dynamically-imported dependencies — always test the built binary rather than assuming it matches the interpreted run. A reasonable pattern is PyInstaller during development for fast iteration, Nuitka for release builds once the app is stable. If adopted, `build.ps1` keeps its name and its `dist/release/` destination (`--output-dir`).

---

### Windows installer — NSIS, per user

For a hand-out beyond "unzip the folder", `package.ps1` builds a per-user installer from the `--onedir` output with `references/nsis/installer.nsi` (copied to `installer/`, with `path.nsh` and `upgrade.nsh` beside it). It installs under `%LOCALAPPDATA%\Programs`, so there is no UAC prompt; the same two includes serve the Go/Wails installer.

- **`path.nsh`** — an optional, ticked-by-default component that **appends** the install folder to the user `PATH` and removes only that entry on uninstall. It never rewrites what it cannot read back intact: a `PATH` of 1000+ characters (NSIS strings stop at 1023 and `ReadRegStr` truncates silently) is left alone and the user is told in a dialog. Only useful if the folder holds something to run from a terminal: the app, or a CLI built into the same folder (one `.spec`, two `EXE`, one `COLLECT`; `/DAPP_EXTRA_EXE="myapp-cli.exe"`).
- **`upgrade.nsh`** — updating by running a newer installer: reuse the installed folder, refuse a downgrade (exit code 2), wait for the app and `APP_EXTRA_EXE` to be closed (silent: exit code 5). `installer.nsi` wires `AppCheckInstalled`, `AppWaitForExit` and the `InstallLocation` value, and clears `_internal\` before copying so an update leaves no stale libraries.
- **Version**: pass `INFO_PRODUCTVERSION` from `pyproject.toml`; a pre-release suffix (`1.2.0-beta.2`) needs a digits-only `INFO_FILEVERSION` as well.
- **Try it against a scratch key**: `/DAPP_ENV_KEY="Software\<co>\Scratch"` redirects the `PATH` edit away from the real `HKCU\Environment`. Run it silently (`/S /D=<folder>`) through install, update, downgrade and uninstall before shipping.
- **`makensis` without admin rights**: the NSIS zip, unpacked into the user profile — `references/nsis/install-nsis.md`.
- Sign the installer as well as the executable inside it (§4, antivirus).

## 4b. Where the app writes at runtime

Distinct from where the code lives: where the installed application writes
settings, its database, and its logs. Writing beside the executable works
throughout development and breaks the day the app is installed somewhere the
process can't write — `Program Files`, or a `--onedir` build dropped in a
read-only location — so it surfaces at the user's site, not on the developer's
machine.

`QSettings` (P5) already covers preferences. For everything else, resolve the
path from `QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)`
(and `AppLocalDataLocation` for caches). Resolve it once in `settings.py` and
pass it into `core/` — `core/` should receive a path, never compute one from
`__file__` or `sys.argv[0]`, which is what ties it to the interface process and
breaks the moment a CLI or a scheduled job reuses it. A tkinter tool has no
`QStandardPaths`: use `%APPDATA%\<name>` (`os.environ["APPDATA"]`) on Windows,
resolved the same way, once, outside `core/`.

---

## 5. Scaffolding rules

1. Settle the interface layer and the distribution stakes first (who receives it, startup time, sensitive logic). Ask if the information is missing — these set P3 and P4.
2. **Scaffold with `uv init --package <name>`**, then reshape into §1 or §2. It produces the `src/` layout, `.python-version` and the `.gitignore`; add `.build/` and `.env` to the latter.
3. Only create folders actually used. No placeholder for a layer that isn't justified yet.
4. `__main__.py`: bootstrap only — create the application object and the main window, nothing else.
5. `core/errors.py` with `AppError` (§3b), the worker pattern (§3) and the exception hooks from the first screen, even minimal: these are the boundaries most expensive to introduce late.
6. No `cli/`, no `packages/` and no workspace without the consumer that needs it (§2b).
7. **Nothing runs at import time** in `core/`, `cli/`, or the package's own `__init__.py`: no file read, no connection, no framework import. The gate imports every one of those modules to check the boundary, and a CLI imports them on every start.
8. Generate nothing tied to a forge or CI system.
9. Document P1–P6 in the project README.
10. **Pin the interpreter and move it as one.** `.python-version`, `requires-python`, ruff's `target-version` and mypy's `python_version` name the same minor, which both PySide6 and PyInstaller must support — not the newest release by reflex. `uv.lock` is committed; dependency upgrades go in their own commit, and a PySide6 or PyInstaller upgrade is followed by a build tested on a clean machine (§4).
11. **Scripts keep the same names in every project**, under `scripts/`, so a colleague moving between apps does not guess:

    | Script | Means |
    |---|---|
    | `dev.ps1` | the app run from source, console attached (`uv run python -m <name>`) |
    | `check.ps1` | the full gate: `uv sync --locked`, `ruff format --check`, `ruff check`, `mypy`, `pytest`, then the GUI-free code checked free of interface frameworks; `-Fast` skips the tests (`references/check.ps1`, copied as-is unless the gate needs more) |
    | `build.ps1` | the release build into `dist/release/` (§4) |
    | `package.ps1` | the installer, or the zipped `--onedir` folder, signed, with hand-out copies if the project ships any |
    | `release.ps1` | publishing what `package.ps1` produced |

    Other scripts are fine (`build-debug.ps1`, `sign.ps1`...); these names always mean the same thing, and match the Tauri and Wails branches'. Tauri has a sixth, `clean.ps1`, with no equivalent here: uv's cache lives outside the project, and PyInstaller rewrites `.build/` on each build (`python-code-standards`, `build-and-disk.md`).
12. **No dev port to allocate**: there is no web dev server in this branch, unlike the webview ones.
13. `python-code-standards` for the ruff and mypy configuration and the build pinning.

---

## 6. Protecting sensitive logic in detail

**Start from: most tools need nothing here.** Internal utilities rarely warrant protection, and adding it costs build complexity for no benefit. Apply this only when something specific must not be easily read.

**What plain PyInstaller gives you: effectively nothing.** It bundles Python bytecode, and freely available decompilers recover close-to-original source from it. Assume anything shipped this way is readable.

**The approach that works: compile the sensitive part only.** Because `core/` is already separated from the interface (§1), a single module can be compiled into a native extension while everything else stays ordinary Python.

**Cython** — the lighter option:

```bash
cythonize -i src/myapp/core/sensitive.py
```

Produces a `.so`/`.pyd` that imports exactly like the original module. Cython's maintainers state plainly it is not an obfuscation tool: it raises the bar against casual reading, but the generated C still contains visible calls into Python's C API that reveal structure. Right choice for "shouldn't be trivially readable."

**Rust via PyO3** — meaningfully stronger. A real compiled binary with no Python structure showing through; research on decompiling Rust confirms its generics, traits and release-mode optimizations substantially degrade decompilation quality. Costs real learning time — though if the team is also adopting Rust for the web-based branch, the investment serves both.

**The ceiling, stated honestly**: neither prevents a determined attacker with a disassembler from recovering logic. If something genuinely must not leave your control, keep it on a server you control and have the app call it. That requires network access the app may not have — for an offline field tool, it simply isn't available, and saying so is more useful than recommending it anyway.

---

## 7. Anti-patterns — audit checklist

| # | Symptom | Diagnosis |
|---|---|---|
| 1 | Blocking work directly in a button handler or event callback | Freezes the interface — highest-priority class of bug |
| 2 | `PySide6` or `tkinter` imported inside `core/`, directly or through another module | Logic not actually separated; untestable, unreusable, can't be compiled alone. The gate fails on it |
| 3 | Widgets updated from a background thread | Race conditions; in tkinter, outright unsafe |
| 4 | `QThread` subclassed with logic inside `run()` | Couples work to thread; prefer a worker object moved to a thread |
| 5 | Global mutable variables instead of explicit state objects | Hard to reason about, worse under threading |
| 6 | No global exception hook | Crashes in callbacks disappear silently with no diagnostic trail |
| 7 | `--onefile` shipped to users with startup complaints | Known trade-off, never revisited — check `--onedir` or Nuitka |
| 8 | Externally distributed and unsigned | Predictable SmartScreen and antivirus friction |
| 9 | Sensitive logic shipped with packaging as the only protection | Packaging treated as a security boundary it cannot be |
| 10 | Elaborate protection on a tool nobody would reverse-engineer | Cost with no corresponding risk — mismatch in the other direction |
| 11 | Settings written ad hoc to files instead of `QSettings` (PySide6) | Reinvents cross-platform config storage Qt already provides |
| 12 | No tests exercising `core/` without launching the interface | Confirms logic and interface were never separated |
| 13 | Built app never tested on a machine other than the developer's | Missing Qt plugins and missing runtime dependencies surface only there |
| 14 | tkinter tool that has grown to many screens | Past the point tkinter serves well — move to PySide6 |
| 15 | A `packages/` workspace whose core nothing installs without the app | Overhead with nothing to justify it — a CLI alone doesn't need it (§2b) |
| 16 | `core/` functions passing live handles or framework objects in signatures | Blocks any later move to a network boundary (§9) |
| 17 | Writes configuration, database or logs beside the executable | Breaks on any read-only or per-machine install; surfaces only after deployment (§4b) |
| 18 | `str(exc)` shown to the user or emitted by a worker, or no `AppError` | Paths and internals reach the screen; the interface has nothing to branch on (§3b) |
| 19 | No `uv.lock` committed, or a release built from an environment never synced against it | The artifact depends on the build machine and the day (§4) |
| 20 | `core/` or `cli/` module doing work at import time | Slows every CLI start; breaks the gate's boundary check (§5, rule 7) |
| 21 | Long-running `core/` call with no progress or cancellation | Frozen-looking UX, no way out for the user (§3) |
| 22 | The `PySide6` meta-package with only Essentials modules used | Addons weight shipped for nothing (§4) |
| 23 | Off the common layout: flat layout, a `build.py`, scripts under other names, no `scripts/check.ps1` | Nothing copies between projects; ranked low, moving it is mechanical (§1, §5) |

**Reporting priority**: user-visible impact first (1, 3, 6, 13), then the boundary (2, 12, 18) — the ones that compound — then layout and naming.

---

## 8. Prompts (standalone use)

**New project**
```
Set up a new Python desktop project: scaffold with `uv init --package`, then
the common layout (src/, scripts/, uv.lock, .python-version), ui/ and core/
separated with no framework imports in core/, AppError in core/errors.py, a
worker pattern for anything that blocks, a global exception hook, and
scripts/check.ps1 copied from the reference.
Ask me first: PySide6 or tkinter, who receives the app, whether startup time
matters, and whether any logic is sensitive — don't default silently.
```

**Audit**
```
Audit this Python desktop project:
1. Run scripts/check.ps1 if present; otherwise check whether core/ imports
   PySide6 or tkinter, directly or through another module.
2. Any blocking work reachable from an interface callback?
3. Do errors reach the user as AppError codes, or as str(exc)?
4. Is packaging appropriate for who actually receives this — onedir vs onefile,
   signed or not, built from uv.lock?
5. Does the level of source protection match the actual risk, in either direction?
6. Is the project on the common layout (§1) and script names (§5)?
Walk the §7 checklist. Rank by user-visible impact first, then structural debt.
Evidence with file and line. Modify no files.
```

**Packaging and protection decision**
```
Help me decide how to ship this app. Ask about: who receives it, whether startup
time matters, whether any specific logic must not be easily read, and whether the
app can reach a network.
Then recommend a packaging approach with concrete commands, and say plainly
whether any protection step is warranted — including if the answer is none.
```

**Adding a CLI or a second consumer**
```
Per §2b, I want <a CLI / a server / a scheduled job> to use this app's logic.
First: does anything need to install core/ without the app, or is this a CLI
shipped beside it? For a CLI, lay out the dual-mode and two-executables options
and ask me which fits. Check the prerequisite either way: does scripts/check.ps1
pass the boundary step? If not, list what to break first. Create no files yet.
```

**Evolving toward a server with remote clients**
```
Assess exposing this app's business logic to remote clients via a server, per §9.
Cover:
1. Which core/ modules are centralizable vs inherently local (files, serial
   ports, hardware) — classify module by module.
2. Whether core/ functions take and return plain, serializable data.
3. What's still unaddressed: multi-user authentication, sessions, data isolation
   between clients.
Produce a plan, don't move code yet.
```

---

## 9. Evolving toward a server with remote clients

Distinct from §2b: there the goal was reuse on the same machine, here it's a server that remote clients connect to over a network. Three points, none of them covered by P1–P6, all easy to get wrong by assuming the §2b mechanics carry over unchanged.

### 1. Not everything in `core/` can move to a server

This branch is frequently chosen precisely for local access — files, serial ports, CAN interfaces, instrument drivers. A remote server has none of that: it cannot reach a client machine's hardware. Before extracting anything, classify each module:

- **Centralizable** — becomes real server-side state (a database, shared configuration), identical for every client.
- **Inherently local** — stays on the client. The desktop app becomes one client among several, calling the server for the shared parts while keeping hardware and file access local.

Decided module by module, as a product question. Assuming the whole of `core/` centralizes is the most common way this migration goes wrong, and it's especially likely in this branch because local access is often the reason the branch was picked.

### 2. Design the `core/` interface as if it were already a network API

Functions taking and returning plain, serializable data convert cleanly into HTTP endpoints later. Functions passing live objects, open file handles, database cursors, or framework types do not — they have to be redesigned before anything can be exposed remotely. Keeping `core/` free of framework types (already required by P1, and checked by the gate) covers most of this; the remaining discipline is avoiding stateful handles in signatures. `AppError`'s code and message (§3b) are already the shape of an API error.

A useful test: could this function's arguments and return value survive being written to JSON and read back? If not, it isn't ready to become an endpoint.

### 3. Multi-user authentication and data isolation are unaddressed

Nothing in a desktop application's design says which remote user may see or modify which data — a desktop app implicitly trusts whoever is at the keyboard. Authentication, sessions, and isolation between clients need their own design pass on the server side. Treat it as separate work, not a byproduct of moving `core/` behind a network.
