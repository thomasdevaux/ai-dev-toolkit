---
name: python-desktop-architecture
description: Choose, scaffold, and audit the architecture of a Python desktop app (PySide6 or tkinter). Use when building, structuring or reviewing one — separating interface, background work and business logic; packaging and distribution (PyInstaller, Nuitka, Cython); download size, startup time, antivirus false positives, or protecting shipped source. Assumes the Python branch is already chosen; if no stack has been settled on, use desktop-app-architecture first.
---

# Python Desktop Architecture

Pick an architecture and a distribution strategy for a Python desktop app, scaffold it, or audit an existing one.

## Scope

Covers the Python branch: **PySide6** for full-featured interfaces, **tkinter** for minimal ones, Python for all the logic, and PyInstaller for shipping — with an optional step for protecting sensitive logic.

**PySide6, not PyQt6**: PySide6 is LGPL and free to use in closed-source commercial software. PyQt6 requires a paid licence for the same use. If a project is already on PyQt6 for a reason the team accepted, the architecture guidance here still applies unchanged — only the licensing note differs.

If the user hasn't settled on the Python branch, defer to `desktop-app-architecture`.

## Choosing the interface layer

**PySide6** is the default. Use it for anything with multiple screens, tables, live-updating data, charts, or a look the user will judge.

**tkinter** only when the tool is genuinely tiny — one window, a few fields, a button — and shipping zero extra dependencies matters more than how it looks. It comes with Python, so there's nothing to install. Its limits are real and worth stating out loud to the user rather than discovering later: dated appearance, weak support for data-heavy views, and no good story for live-updating tables or charts. If a tkinter tool starts growing screens, that's the signal to move to PySide6, and the move is cheaper if the logic was kept out of the interface code from the start (see below).

## Core idea

Two decisions carry disproportionate weight. Both are easy to skip because a first prototype works fine without them.

- **Keeping logic out of the interface.** Business logic must live in plain Python with no imports from PySide6 or tkinter. This is what makes the logic testable on its own, reusable if the interface is ever replaced, and — importantly — it's the same separation that later lets you compile just the sensitive parts.
- **The background-work boundary.** A Python desktop app has exactly one interface thread. Anything that blocks it — reading files, network calls, talking to hardware, heavy computation — freezes the window. Get this wrong early and every screen ends up with ad hoc patches instead of a proper worker model.

## Two structural states

Unlike the web-based branch, there's no profile spectrum here. With a single language and no technical boundary between interface and logic, the only structural question that matters is binary:

- **Application-only** (default) — `core/` lives inside the app's package. Right for almost every tool.
- **Reusable logic** — `core/` becomes a package in its own right, with a second consumer alongside the app: a CLI, a scheduled job, a server. Only move here when that second consumer actually exists, not in anticipation.

**Why the boundary is weaker here than in other branches, and what to do about it.** In Tauri or Wails, a genuine technical barrier separates interface from logic — a function is either exposed across it or it isn't. In Python, the interface calls `core/` by ordinary function call, so nothing enforces the separation. It stays intact by discipline alone, and dissolves quietly: an import of a widget class "just for a type hint," a service reaching up to show a dialog, and the boundary is gone without anything breaking.

Two things that make it real rather than aspirational:
- **Test `core/` in a test suite that never constructs an application object.** If those tests still pass, the separation holds. If they start needing a `QApplication`, it has already broken.
- **When reuse becomes likely, make `core/` an actually installable package** with its own `pyproject.toml`, installed into the app's environment. An import that would cross the boundary the wrong way then fails at install/import time rather than silently working.

## The six decisions

| # | Decision | Default |
|---|---|---|
| P1 | Where does business logic live? | Plain Python modules with no interface-framework imports |
| P2 | How is blocking work handled? | Worker objects on background threads, results sent back via signals (PySide6) or a queue polled by the main loop (tkinter) |
| P3 | How is the app packaged? | PyInstaller, `--onedir` unless a single file is genuinely required |
| P4 | Is any logic sensitive enough to compile? | By default no. If yes, compile only that part (see below) |
| P5 | Settings and app state | `QSettings` for user preferences in PySide6; explicit state objects rather than globals in both |
| P6 | Error handling | A single global handler wired to `sys.excepthook`, with user-facing messages kept separate from logged detail |

P1 and P4 are the ones worth real time.

## Packaging and protecting the app

**Packaging: PyInstaller.** It bundles Python itself plus all dependencies into something the user can run without installing anything. Two things to tell the user plainly, because both surprise people late:

- **`--onedir` over `--onefile` by default.** A single-file build unpacks itself into a temporary folder on every launch, which is the most common cause of "why does this take so long to start." A folder-based build starts noticeably faster. Only use `--onefile` when distributing a single file is a hard requirement.
- **Antivirus false positives are a real, documented problem**, not an edge case. Windows Defender and SmartScreen frequently flag PyInstaller executables, because bundling an interpreter and self-extracting at startup looks structurally like what malware does. This is worth raising *before* the app is distributed externally, not after a client refuses to run it. Mitigations that actually help: use the latest PyInstaller, prefer `--onedir`, and sign the executable (code signing doesn't stop anyone reading your code, but it establishes the publisher's identity and largely resolves SmartScreen warnings).

**Protecting sensitive logic: compile that part, not the whole app.** The default assumption should be that no protection is needed — most internal tools don't warrant it. When something genuinely must not be easily read (a proprietary algorithm, a vendor-confidential sequence), the effective approach is to move that specific piece into a compiled extension module while the rest of the app stays ordinary Python:

- **Cython** is the lighter option: near-Python syntax, quick for a Python developer to pick up. Its maintainers are explicit that it is *not* an obfuscation tool — it raises the bar against casual reading, and the generated C still carries visible traces of Python's internals. Right choice when the goal is "not trivially readable."
- **Rust via PyO3** is meaningfully stronger: a genuine compiled binary with no Python structure showing through. Costs real learning time — unless the team is already going to learn Rust for the web-based branch, in which case the investment serves twice. Right choice when exposure is a real business risk rather than a preference.

**Be honest about the ceiling.** Neither makes anything unreadable to a determined attacker with the right tools. If some logic genuinely must not leave your control, the answer is architectural, not a compiler flag: keep it on a server you control and have the app call it. That's only possible when the app can reach a network, which rules it out for many offline field tools — say so rather than recommending it blindly.

**Nuitka** is worth mentioning as an alternative to PyInstaller when startup time or whole-program speed is the main concern: it compiles the whole application to a native binary, which starts faster and runs faster. It costs longer builds and occasional friction with dynamically-imported dependencies. It is a packaging improvement, not a substitute for the targeted protection above.

## Workflow: scaffolding a new project

1. **Confirm the interface layer** — PySide6 unless the tool is genuinely tiny. If the user asks for tkinter, check the tool really is that small, and say plainly what tkinter can't do well.
2. **Ask about distribution stakes before assuming**: who receives this, does startup time matter, is any logic sensitive? These set P3 and P4 and shouldn't be defaulted silently.
3. **Read `references/architecture.md`** for the folder structure and the full packaging detail.
4. **Separate logic from interface in the very first files.** A `core/` package with no framework imports, and a `ui/` package that calls into it. This is what makes everything else possible later.
5. **Set up the background-work pattern early**, before any screen has a blocking call in it.
6. **Wire the global error handler** from the start, not after the first silent crash in the field.
7. **Decide packaging explicitly** and document it, rather than letting it default to whatever a tutorial used.

## Workflow: auditing an existing project

1. **Read `references/architecture.md`** (anti-pattern checklist).
2. **Check the background-work boundary first** — any blocking call reachable from a button handler is the highest-priority finding, because users feel it directly.
3. **Check for framework imports inside logic code.** If the logic package imports PySide6 or tkinter, it isn't actually separated, whatever the folder names suggest.
4. **Assess packaging against real stakes**: is this distributed externally with `--onefile` and no signing, with startup or antivirus complaints? That's a finding, not a style preference.
5. **Check whether protection matches the risk** — either sensitive logic shipped with nothing at all, or elaborate protection on a tool nobody would bother reverse-engineering. Both are mismatches.
6. **Rank by user-visible impact first** (freezing, crashes, install friction), then structural debt.
7. **Modify no files** unless the user asks for fixes.

## Workflow: moving to reusable logic

When a real second consumer appears (a CLI, a scheduled job, a server):

1. **If the second consumer is a CLI companion to the app, ask which of two shapes fits — never default**: a single script that branches on arguments before importing the interface (stays inside the app, no new packages), or a genuinely separate installable package (heavier, but lean and boundary-enforced). See `references/architecture.md` §2b for both, with the trade-off.
2. **Check the prerequisite first**: does `core/` import PySide6 or tkinter anywhere? If yes, list what to break before extracting anything — extraction on top of a broken separation is what makes this expensive.
3. **Promote `core/` to its own package** with its own `pyproject.toml`, installed into the app's environment rather than imported by path — only if the separate-package shape was chosen.
4. **Add the second consumer alongside the app**, both depending on that package — neither depending on the other.
5. **Justify it by the consumer that exists**, not the one that might.

## Workflow: evolving toward a server with remote clients

Different from the reuse case above: here the goal is a server that remote clients connect to. Three things need surfacing, because none are covered by P1–P6 and all three are easy to get wrong.

1. **Not everything in `core/` can move to a server.** This branch is often chosen precisely for local access — files, serial ports, CAN interfaces, local hardware. A remote server cannot reach a client's hardware. Go module by module and classify each as centralizable (becomes real server-side state) or inherently local (stays on the client, which becomes one client among several). This is a product decision, not a mechanical refactor, and assuming everything centralizes is the most common way this goes wrong.
2. **Design the `core/` interface as if it were already a network API.** Functions that take and return plain, serializable data — rather than passing around live objects, open handles, or framework types — convert cleanly to HTTP endpoints later. Work spent here is reused directly rather than redone.
3. **Multi-user authentication and data isolation are a separate, unaddressed problem.** Nothing in a desktop app's design covers which remote user may see which data. It needs its own design pass on the server side.

## Reference file

`references/architecture.md` — folder structures for both PySide6 and tkinter, the background-work patterns in full, the packaging and protection detail with concrete commands, and the anti-pattern checklist.
