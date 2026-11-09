---
name: python-desktop-architecture
description: Choose, scaffold, and audit the architecture of a Python desktop app (PySide6 or tkinter). Use when building, structuring or reviewing one — layout, scripts and check gate, separating interface, background work and logic, errors, adding a CLI; packaging (PyInstaller, Nuitka, Cython), startup time, antivirus false positives, protecting shipped source. Assumes the Python branch is already chosen; if no stack has been settled on, use desktop-app-architecture first.
---

# Python Desktop Architecture

Pick an architecture and a distribution strategy for a Python desktop app, scaffold it, or audit an existing one against it.

## Scope

Covers the Python branch: **PySide6** for full-featured interfaces, **tkinter** for minimal ones, Python for all the logic, **uv** for the environment, and PyInstaller for shipping — with an optional step for protecting sensitive logic.

**PySide6, not PyQt6**: PySide6 is LGPL and free to use in closed-source commercial software. PyQt6 requires a paid licence for the same use. If a project is already on PyQt6 for a reason the team accepted, the architecture guidance here still applies unchanged — only the licensing note differs.

If the user hasn't settled on the Python branch, defer to `desktop-app-architecture`.

## Choosing the interface layer

**PySide6** is the default. Use it for anything with multiple screens, tables, live-updating data, charts, or a look the user will judge.

**tkinter** only when the tool is genuinely tiny — one window, a few fields, a button — and shipping zero extra dependencies matters more than how it looks. It comes with Python, so there's nothing to install. Its limits are real and worth stating out loud to the user rather than discovering later: dated appearance, weak support for data-heavy views, and no good story for live-updating tables or charts. If a tkinter tool starts growing screens, that's the signal to move to PySide6, and the move is cheaper if the logic was kept out of the interface code from the start (see below).

## Core idea

Two decisions carry disproportionate weight. Both are easy to skip because a first prototype works fine without them.

- **Keeping logic out of the interface.** Business logic must live in plain Python with no imports from PySide6 or tkinter. This is what makes the logic testable on its own, reusable if the interface is ever replaced, and — importantly — it's the same separation that later lets you compile just the sensitive parts.
- **The background-work boundary.** A Python desktop app has exactly one interface thread. Anything that blocks it — reading files, network calls, talking to hardware, heavy computation — freezes the window. Get this wrong early and every screen ends up with ad hoc patches instead of a proper worker model.

## The layout (the same for every app)

Every Python app of the portfolio has the same top-level shape, whatever its interface layer:

```text
my-app/
├── src/<name>/          # the one package: __main__.py, ui/, core/, workers/
├── tests/               # tests core/ without constructing the application
├── scripts/             # dev, check, build, package, release
├── pyproject.toml       # project, dev dependency group, ruff and mypy config
├── uv.lock              # committed
└── .python-version      # the interpreter, pinned
```

Why one layout: scripts, the gate and the docs are copied between projects unchanged, a colleague moving between apps — Python, Tauri or Wails — finds the same script names, and adding a CLI later is an addition (`src/<name>/cli/`), never a move. It is what `uv init --package` generates, reshaped. Full trees are in `references/architecture.md` §1–§2.

**Why the boundary needs a gate here, and what the gate does.** In Tauri, the core crate has no Tauri dependency to reach for, so the compiler keeps the framework out. In Python, the interface and `core/` meet by ordinary import, so nothing enforces the separation: an import of a widget class "just for a type hint", a service reaching up to show a dialog, and the boundary is gone without anything breaking. **`references/check.ps1`, copied as `scripts/check.ps1`, supplies the guarantee**, as Wails' gate does for `internal/domain`: it imports every module of `core/` (and `cli/`, and any `packages/`) and fails when PySide6 or tkinter ends up loaded, directly or through another module, and it reads the files for an import hidden inside a function. Testing `core/` in a suite that never constructs a `QApplication` is the other half: if those tests start needing one, the separation has already broken.

## Two structural states

Unlike the webview branches, there's no profile spectrum here: with a single language and no technical boundary between interface and logic, the only structural question is binary.

- **Application-only** (default) — `core/` lives inside the app's package. Right for almost every tool, including one that ships a CLI beside the app.
- **Reusable logic** — `core/` becomes a package of its own in a uv workspace (`packages/<name>-core/`), with the app still at the root. Only when something must **install** the logic without the app — a server, a scheduled job on another machine — and only once it exists.

**If the second consumer is a CLI companion to the app, there are two ways to build it — never default, always ask which one fits.** Neither needs the second state:

| | Single executable, dual-mode | Two executables, one package |
|---|---|---|
| What ships | One executable — runs as CLI with arguments, opens the window with none | Two executables, built from the same `src/<name>/` |
| CLI weight | Bundles PySide6, imports it only in the window branch | Lean — PyInstaller follows imports, so the CLI build contains no Qt |
| Guarantee against interface code leaking into CLI logic | None but discipline | The gate, which checks `cli/` like `core/` |
| Folder shape needed | None — a branch in `__main__.py` (`references/architecture.md` §2b) | An added `src/<name>/cli/`, and a second PyInstaller entry (§2b) |
| Fits best | Simple distribution, occasional CLI use | CLI invoked repeatedly in scripts or CI, where startup time and size matter |

## The six decisions

| # | Decision | Default |
|---|---|---|
| P1 | Where does business logic live? | `core/`: plain Python modules with no interface-framework imports, nothing run at import time |
| P2 | How is blocking work handled? | Worker objects on background threads, results sent back via signals (PySide6) or a queue polled by the main loop (tkinter); beyond ~500 ms, progress and a `threading.Event` to cancel |
| P3 | How is the app packaged? | PyInstaller from the locked environment, `--onedir` unless a single file is genuinely required, into `dist/release/` |
| P4 | Is any logic sensitive enough to compile? | By default no. If yes, compile only that part (see below) |
| P5 | Settings and app state | `QSettings` for user preferences in PySide6; explicit state objects rather than globals in both; runtime paths resolved once, outside `core/` |
| P6 | Error handling | `core/` raises one typed `AppError` (stable `code`, safe `message`) that the interface switches on — never `str(exc)` on screen; a global handler on `sys.excepthook` for everything else, user-facing message kept separate from logged detail |

P1 and P4 are the ones worth real time. P6 is the one most often skipped, and the expensive one to retrofit once workers emit strings.

## Packaging and protecting the app

**Packaging: PyInstaller**, from the environment `uv.lock` describes. It bundles Python itself plus all dependencies into something the user can run without installing anything. Three things to tell the user plainly, because all three surprise people late:

- **`--onedir` over `--onefile` by default.** A single-file build unpacks itself into a temporary folder on every launch, which is the most common cause of "why does this take so long to start." A folder-based build starts noticeably faster. Only use `--onefile` when distributing a single file is a hard requirement.
- **`PySide6-Essentials` over the `PySide6` meta-package** unless an Addons module is used: the meta-package's Addons weigh on the download for nothing.
- **Antivirus false positives are a real, documented problem**, not an edge case. Windows Defender and SmartScreen frequently flag PyInstaller executables, because bundling an interpreter and self-extracting at startup looks structurally like what malware does. This is worth raising *before* the app is distributed externally, not after a client refuses to run it. Mitigations that actually help: use the latest PyInstaller, prefer `--onedir`, and sign the executable (code signing doesn't stop anyone reading your code, but it establishes the publisher's identity and largely resolves SmartScreen warnings).

**Protecting sensitive logic: compile that part, not the whole app.** The default assumption should be that no protection is needed — most internal tools don't warrant it. When something genuinely must not be easily read (a proprietary algorithm, a vendor-confidential sequence), the effective approach is to move that specific piece into a compiled extension module while the rest of the app stays ordinary Python:

- **Cython** is the lighter option: near-Python syntax, quick for a Python developer to pick up. Its maintainers are explicit that it is *not* an obfuscation tool — it raises the bar against casual reading, and the generated C still carries visible traces of Python's internals. Right choice when the goal is "not trivially readable."
- **Rust via PyO3** is meaningfully stronger: a genuine compiled binary with no Python structure showing through. Costs real learning time — unless the team is already going to learn Rust for the web-based branch, in which case the investment serves twice. Right choice when exposure is a real business risk rather than a preference.

**Be honest about the ceiling.** Neither makes anything unreadable to a determined attacker with the right tools. If some logic genuinely must not leave your control, the answer is architectural, not a compiler flag: keep it on a server you control and have the app call it. That's only possible when the app can reach a network, which rules it out for many offline field tools — say so rather than recommending it blindly.

**Installer: NSIS, per user** — when "unzip the folder" is not enough, `references/nsis/installer.nsi` builds an installer that needs no admin rights, with an optional user `PATH` entry and update-in-place (refuses a downgrade, waits for the app to close). `makensis` itself installs without admin rights from the NSIS zip (`references/nsis/install-nsis.md`). Details in `references/architecture.md` §4.

**Nuitka** is worth mentioning as an alternative to PyInstaller when startup time or whole-program speed is the main concern: it compiles the whole application to a native binary, which starts faster and runs faster. It costs longer builds and occasional friction with dynamically-imported dependencies. It is a packaging improvement, not a substitute for the targeted protection above.

## Workflow: scaffolding a new project

1. **Confirm the interface layer** — PySide6 unless the tool is genuinely tiny. If the user asks for tkinter, check the tool really is that small, and say plainly what tkinter can't do well.
2. **Ask about distribution stakes before assuming**: who receives this, does startup time matter, is any logic sensitive? These set P3 and P4 and shouldn't be defaulted silently.
3. **Propose before building**: the interface layer and P1–P6, and get agreement.
4. **Read `references/architecture.md`** (§1–§2 for the tree, §5 for the scaffolding rules).
5. **Scaffold with `uv init --package <name>`**, then reshape into the common layout rather than writing it from memory.
6. **Separate logic from interface in the very first files.** A `core/` package with no framework imports and `core/errors.py` holding `AppError`, a `ui/` package that calls into it.
7. **Set up the background-work pattern early**, before any screen has a blocking call in it.
8. **Wire the global error handler** from the start, not after the first silent crash in the field.
9. **Set up the fixed pieces** (§5): the pinned interpreter and `uv.lock`, the script names with `references/check.ps1` as `scripts/check.ps1`, `dist/release` and `dist/debug` for builds, and `python-code-standards` for ruff, mypy and the build pinning.
10. **Create only what is used.** No empty folders, no `cli/` or `packages/` before their consumer.
11. **Generate nothing tied to a forge or CI system.** No `.github/`, no `.gitlab-ci.yml`, no pipeline files, unless the user explicitly asks.
12. **Document P1–P6 and the packaging decision in the project README.**

## Workflow: auditing an existing project

1. **Read `references/architecture.md`** (§7 anti-pattern checklist, §3–§3b).
2. **Run the gate** if the project has `scripts/check.ps1`; otherwise, check for framework imports inside logic code by hand — directly and through other modules. If the logic package imports PySide6 or tkinter, it isn't actually separated, whatever the folder names suggest.
3. **Check the background-work boundary** — any blocking call reachable from a button handler is the highest-priority finding, because users feel it directly.
4. **Check the error boundary**: does the user see `AppError` messages, or `str()` of whatever was raised?
5. **Assess packaging against real stakes**: is this distributed externally with `--onefile` and no signing, with startup or antivirus complaints? Built from `uv.lock`? That's a finding, not a style preference.
6. **Check whether protection matches the risk** — either sensitive logic shipped with nothing at all, or elaborate protection on a tool nobody would bother reverse-engineering. Both are mismatches.
7. **Check the layout and the script names.** A project off the common layout is a finding too, ranked low: moving it is mechanical.
8. **Rank by user-visible impact first** (freezing, crashes, install friction), then structural debt, with file and line as evidence.
9. **Modify no files** unless the user asks for fixes.

## Workflow: adding a CLI or moving to reusable logic

When a real second consumer appears (a CLI, a scheduled job, a server):

1. **Tell the two cases apart**: a CLI shipped beside the app stays application-only; something that installs the logic without the app is the reusable-logic state.
2. **For a CLI, ask which of the two shapes fits — never default** (table above, `references/architecture.md` §2b).
3. **Check the prerequisite first**: does the gate's boundary step pass? If not, list what to break before extracting anything — extraction on top of a broken separation is what makes this expensive.
4. **For reusable logic**: turn the root into a uv workspace, move `core/` to `packages/<name>-core/` with its own `pyproject.toml`, add the consumer beside it, keep one `uv.lock`. The gate checks every package under `packages/`.
5. **Justify it by the consumer that exists**, not the one that might.

## Workflow: evolving toward a server with remote clients

Different from the reuse case above: here the goal is a server that remote clients connect to. Three things need surfacing, because none are covered by P1–P6 and all three are easy to get wrong.

1. **Not everything in `core/` can move to a server.** This branch is often chosen precisely for local access — files, serial ports, CAN interfaces, local hardware. A remote server cannot reach a client's hardware. Go module by module and classify each as centralizable (becomes real server-side state) or inherently local (stays on the client, which becomes one client among several). This is a product decision, not a mechanical refactor, and assuming everything centralizes is the most common way this goes wrong.
2. **Design the `core/` interface as if it were already a network API.** Functions that take and return plain, serializable data — rather than passing around live objects, open handles, or framework types — convert cleanly to HTTP endpoints later. Work spent here is reused directly rather than redone.
3. **Multi-user authentication and data isolation are a separate, unaddressed problem.** Nothing in a desktop app's design covers which remote user may see which data. It needs its own design pass on the server side.

## Reference files

- `references/architecture.md` — §1 common layout and the PySide6 tree, §2 tkinter, §2b CLI access and reusable logic, §3 background work, §3b the error boundary, §4 packaging (PyInstaller, Nuitka, the NSIS installer), §4b runtime data and log locations, §5 scaffolding rules, §6 protecting sensitive logic, §7 the anti-pattern checklist, §8 standalone prompts, §9 evolving toward a server with remote clients.
- `references/check.ps1` — the gate, copied to `scripts/check.ps1`.
- `references/nsis/` — the per-user Windows installer: `installer.nsi` (template for a PyInstaller `--onedir` build), `path.nsh` (optional user `PATH` entry), `upgrade.nsh` (update in place), `install-nsis.md` (getting `makensis` without admin rights, from the zip). Architecture §4.
- The ruff and mypy configuration, and the interpreter and lockfile pinning, are the `python-code-standards` skill of the same block.

For scaffolding, §1, §5 and §3b are usually enough. For an audit, §7 and §3.
