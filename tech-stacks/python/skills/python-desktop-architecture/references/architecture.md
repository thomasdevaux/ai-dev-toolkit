# Reference — Python Desktop Architecture (PySide6 / tkinter)

Folder structures, background-work patterns, packaging and protection detail, audit checklist.

**Contents**
1. Folder structure — PySide6
2. Folder structure — tkinter
2b. Folder structure — reusable logic
3. Background work in detail
4. Packaging in detail
4b. Where the app writes at runtime
5. Protecting sensitive logic in detail
6. Anti-patterns — audit checklist
7. Prompts (standalone use)
8. Evolving toward a server with remote clients

---

## 1. Folder structure — PySide6

```text
my-app/
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── __main__.py           # entry point: QApplication setup only
│       ├── ui/                   # windows, dialogs, widgets — framework code only
│       │   ├── main_window.py
│       │   └── widgets/
│       ├── core/                 # business logic — NO PySide6 imports, testable alone
│       │   ├── __init__.py
│       │   └── <domain>.py
│       ├── workers/              # background-work wrappers around core/ calls
│       │   └── <task>_worker.py
│       ├── state.py              # explicit app state objects, not globals
│       ├── settings.py           # QSettings wrapper
│       └── errors.py             # exception hook, error types
├── tests/
│   └── test_<domain>.py          # tests core/ directly, no QApplication needed
├── resources/
│   ├── icons/
│   └── qss/                      # stylesheets, if used
├── pyproject.toml
├── uv.lock                        # locked environment, committed (see §4)
├── build.py                       # packaging entry point (see §4)
└── README.md
```

**The rule that matters**: `core/` must never import `PySide6`. If it does, the logic can't be tested without launching an application, can't be reused if the interface changes, and can't be cleanly compiled on its own later (§5).

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
│       │   └── <domain>.py
│       ├── state.py
│       └── errors.py
├── tests/
├── pyproject.toml
├── uv.lock
└── README.md
```

**If this grows past two or three screens, that's the signal to move to PySide6.** Because `core/` has no tkinter imports, the move means rewriting the interface only — the logic and its tests carry over unchanged. This is the main practical reason to keep the separation even in a small tool.

## 2b. Folder structure — reusable logic

Only once a second consumer actually exists (a CLI, a scheduled job, a server). Two ways to give the app CLI access — never default, always ask which one fits:

| | Single script, dual-mode | Separate installable package |
|---|---|---|
| What ships | One entry point — runs as CLI with arguments, opens the window with none | A `core` package plus separate app and CLI packages |
| CLI weight | Imports PySide6 whether or not a window is opened | Lean — the CLI doesn't need to import PySide6 at all |
| Guarantee against interface code leaking into CLI logic | None but discipline | Enforced at install time — the CLI package doesn't depend on the interface package |
| Fits best | Simple distribution, occasional CLI use | CLI invoked repeatedly in scripts or CI, where import weight and startup time matter |

**Single script, dual-mode** stays inside §1's shape — no new packages, just a branch in `__main__.py`:

```python
# __main__.py
import sys

def main():
    if len(sys.argv) > 1:
        from myapp.cli import run_cli
        return run_cli(sys.argv[1:])   # CLI mode — PySide6 imported here, not above
    from myapp.ui.main_window import launch
    launch()
```

Importing PySide6 only inside the branch that needs it (rather than at module top level) keeps the CLI path from paying PySide6's import cost even though it's still bundled into the same package.

**Separate installable package** is the heavier option below — reach for it specifically when CLI weight or a compiler-enforced boundary matters, not merely because a CLI was wanted at all.

```text
my-workspace/
├── packages/
│   └── myapp-core/                # installable package, NO interface imports
│       ├── src/myapp_core/
│       │   ├── __init__.py
│       │   └── <domain>.py
│       ├── tests/
│       └── pyproject.toml
│
├── apps/
│   ├── desktop/                   # PySide6 app, depends on myapp-core
│   │   ├── src/myapp/
│   │   │   ├── ui/
│   │   │   ├── workers/
│   │   │   └── __main__.py
│   │   └── pyproject.toml
│   └── cli/                       # second, genuinely separate consumer
│       ├── src/myapp_cli/
│       └── pyproject.toml
│
└── README.md
```

**`apps/`**: no single dominant convention exists for Python monorepos here, so this follows the same `apps/`+`packages/` shape as the web-based skills, which developers moving between projects in this portfolio will already recognize.

**Why make `myapp-core` genuinely installable rather than just a sibling folder**: with `myapp-core` installed into each app's environment, an import that would cross the boundary the wrong way (core reaching into the interface) fails at import time instead of silently working. The separation stops depending on discipline alone — which is the specific weakness of this branch, since nothing else enforces it.

**Don't reach for this layout early.** Until a second, genuinely separate consumer exists, it's overhead: two more `pyproject.toml` files, an install step, and a longer path from edit to run. If a CLI is wanted at all but none of the weight/isolation reasons apply, the dual-mode script above is simpler and gets there with far less structure.

---

## 3. Background work in detail

One interface thread exists. Blocking it freezes the window. The two frameworks solve this differently.

**PySide6** — a worker object moved onto a background thread, communicating back through signals:

```python
class Worker(QObject):
    progress = Signal(int)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            result = core.do_the_work(self.params, on_progress=self.progress.emit)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
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

The background thread pushes progress and results onto the queue; only the main loop touches widgets. **Never update a widget from a background thread in tkinter** — it is not thread-safe and the failures are intermittent and hard to diagnose.

---

## 4. Packaging in detail

**Build from a locked environment.** PyInstaller bundles whatever happens to be
installed, so an unlocked environment makes the shipped artifact depend on the
day it was built and on whose machine built it — which is a large share of the
"it works here but not there" reports the rest of this section warns about.
Manage the environment with `uv` and commit `uv.lock`.

### PyInstaller — the default

```bash
# release
pyinstaller --onedir --windowed --name myapp \
  --distpath dist/release --workpath .build/pyinstaller \
  src/myapp/__main__.py

# debug — no --windowed, so the console stays visible for print/log output
pyinstaller --onedir --name myapp \
  --distpath dist/debug --workpath .build/pyinstaller \
  src/myapp/__main__.py
```

**`--distpath`**: routes the packaged app to `dist/release/` or `dist/debug/` at the repository root, gitignored — the same destination convention as the Go and .NET stacks in this portfolio, so "where's the thing I actually ship" doesn't depend on which of those branches a given tool came from. `dist/` is already PyInstaller's own default here, so this only adds a subfolder. (The Tauri branch deliberately opts out and keeps Cargo's `target/` layout — see that skill's reference for why.) `--workpath` keeps PyInstaller's intermediate files in a dedicated `.build/` folder rather than the default `build/`, which would otherwise collide in meaning with the output folder name used elsewhere. Dropping `--windowed` for the debug build is a deliberate, meaningful difference, not just a naming one: it keeps the console attached so print statements and unhandled exceptions are visible during development testing.

- `--onedir` produces a folder. Starts noticeably faster than `--onefile`, which unpacks itself to a temporary directory on **every** launch.
- `--windowed` suppresses the console window on Windows and macOS.
- Use `--onefile` only when single-file distribution is a hard requirement, and expect the startup cost.

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

Compiles the whole application to a native binary: faster startup, faster execution, no interpreter bundled visibly. Costs longer build times and occasional friction with dynamically-imported dependencies — always test the built binary rather than assuming it matches the interpreted run. A reasonable pattern is PyInstaller during development for fast iteration, Nuitka for release builds once the app is stable.

---

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
breaks the moment a CLI or a scheduled job reuses it.

---

## 5. Protecting sensitive logic in detail

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

## 6. Anti-patterns — audit checklist

| # | Symptom | Diagnosis |
|---|---|---|
| 1 | Blocking work directly in a button handler or event callback | Freezes the interface — highest-priority class of bug |
| 2 | `PySide6` or `tkinter` imported inside `core/` | Logic not actually separated; untestable, unreusable, can't be compiled alone |
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
| 15 | Separate packages/apps layout with only one consumer | Overhead with nothing to justify it — collapse back until a second consumer exists |
| 16 | `core/` functions passing live handles or framework objects in signatures | Blocks any later move to a network boundary (§8) |
| 17 | Writes configuration, database or logs beside the executable | Breaks on any read-only or per-machine install; surfaces only after deployment (§4b) |

---

## 7. Prompts (standalone use)

**New project**
```
Set up a new Python desktop project: src/ layout, ui/ and core/ separated with
no framework imports in core/, a worker pattern for anything that blocks, and a
global exception hook.
Ask me first: PySide6 or tkinter, who receives the app, whether startup time
matters, and whether any logic is sensitive — don't default silently.
```

**Audit**
```
Audit this Python desktop project:
1. Any blocking work reachable from an interface callback?
2. Does core/ import PySide6 or tkinter anywhere?
3. Is packaging appropriate for who actually receives this — onedir vs onefile,
   signed or not?
4. Does the level of source protection match the actual risk, in either direction?
Rank by user-visible impact first, then structural debt. Evidence with file and line.
```

**Packaging and protection decision**
```
Help me decide how to ship this app. Ask about: who receives it, whether startup
time matters, whether any specific logic must not be easily read, and whether the
app can reach a network.
Then recommend a packaging approach with concrete commands, and say plainly
whether any protection step is warranted — including if the answer is none.
```

---

## 8. Evolving toward a server with remote clients

Distinct from §2b: there the goal was reuse on the same machine, here it's a server that remote clients connect to over a network. Three points, none of them covered by P1–P6, all easy to get wrong by assuming the §2b mechanics carry over unchanged.

### 1. Not everything in `core/` can move to a server

This branch is frequently chosen precisely for local access — files, serial ports, CAN interfaces, instrument drivers. A remote server has none of that: it cannot reach a client machine's hardware. Before extracting anything, classify each module:

- **Centralizable** — becomes real server-side state (a database, shared configuration), identical for every client.
- **Inherently local** — stays on the client. The desktop app becomes one client among several, calling the server for the shared parts while keeping hardware and file access local.

Decided module by module, as a product question. Assuming the whole of `core/` centralizes is the most common way this migration goes wrong, and it's especially likely in this branch because local access is often the reason the branch was picked.

### 2. Design the `core/` interface as if it were already a network API

Functions taking and returning plain, serializable data convert cleanly into HTTP endpoints later. Functions passing live objects, open file handles, database cursors, or framework types do not — they have to be redesigned before anything can be exposed remotely. Keeping `core/` free of framework types (already required by P1) covers most of this; the remaining discipline is avoiding stateful handles in signatures.

A useful test: could this function's arguments and return value survive being written to JSON and read back? If not, it isn't ready to become an endpoint.

### 3. Multi-user authentication and data isolation are unaddressed

Nothing in a desktop application's design says which remote user may see or modify which data — a desktop app implicitly trusts whoever is at the keyboard. Authentication, sessions, and isolation between clients need their own design pass on the server side. Treat it as separate work, not a byproduct of moving `core/` behind a network.
