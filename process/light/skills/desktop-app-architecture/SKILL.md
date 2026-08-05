---
name: desktop-app-architecture
description: Help choose a technical stack for a new desktop application, or audit whether an existing app's stack (or a portfolio of tools) still fits. Use whenever the user wants to build a desktop app or internal tool and hasn't settled on a stack ("I want to build a desktop app," "we need an internal tool for X," "what should we use to build this," "can we package this script as an app"). Also use for stack-fit audits, e.g. "should we have built this differently," "this is getting distributed externally now, is that a problem," "we've got too many different stacks across our tools." If the user already named a stack for a new build, or wants a structural review of a project on an already-chosen stack, use the matching specialized skill instead.
---

# Desktop App Architecture — Stack Selection

Help pick a stack for a desktop app, then hand off to a specialized skill that covers that stack in depth. This skill decides *what to build with* and *whether an existing choice still holds* — it never decides folder structure or internals.

## The three branches

Each branch is a coherent bundle: a way to build the interface, a language for the logic behind it, and a way to ship it to users.

```
Python-based
├── Interface: PySide6 (full-featured) or tkinter (minimal)
├── Logic: Python
└── Shipping: PyInstaller, plus optional compilation of sensitive parts
    → skill: python-desktop-architecture

Web-based (interface built with web technology, shown in a desktop window)
├── Interface: React + Vite (escape hatch: plain HTML/JS for very small tools)
├── Logic: Rust or Go
└── Shipping: Tauri (with Rust) or Wails (with Go)
    → skills: rust-webview-desktop-architecture / go-webview-desktop-architecture

.NET-based
├── Interface: Avalonia (XAML)
├── Logic: C# / .NET
└── Shipping: dotnet publish, Native AOT by default
    → skill: dotnet-desktop-architecture

Outside the tree: C++/Qt — a deliberate exception, no detailed skill
```

**"Webview" in two of the skill names** means the interface is a web page rendered by a component the operating system already provides, inside an ordinary desktop window. Nothing is downloaded from the internet and no browser opens — it's a local application that happens to use web technology to draw itself. This is what keeps these apps small: the rendering engine is already on the machine.

**Each branch here is one chosen path, not the whole ecosystem.** Python can also build interfaces with Kivy or wxPython; Rust and Go both have native (non-webview) UI toolkits; .NET has WPF, WinUI and MAUI alongside Avalonia. The skills cover the paths selected as standards, deliberately — if a user asks about one of the alternatives, say plainly that it's outside what these skills cover rather than bending the guidance to fit.

## Present the options before narrowing

**Do not jump straight to whatever the user already knows.** Someone who writes Python daily will often assume Python is the answer and never learn that a different branch would have solved their actual problem better — that's the failure mode this skill exists to prevent. Equally, don't push someone toward an unfamiliar stack just because it's technically stronger.

So: give a short, plain-language tour of all three branches first, framed around what each one is *good at* rather than what it's built with. Then ask what matters most for their case. Then narrow. Two or three sentences per branch is enough — the goal is that the user knows the options exist, not that they become an expert before choosing.

Useful plain-language framing:

- **Python-based** — "You write everything in Python, including the interface. Fastest to build if your team already knows Python, and the easiest to connect to hardware or existing Python tooling. The trade-off is that the finished app is a fairly large download and starts a bit slowly, and some antivirus software is suspicious of Python-packaged executables."
- **Web-based** — "The interface is built with web technology (the same skills as building a website) but runs in a normal desktop window, not a browser. The logic behind it is written in a compiled language, so the finished app is small and starts instantly. The trade-off is learning two new things: the web interface side, and a new backend language."
- **.NET-based** — "Microsoft's ecosystem, using C#. Produces a small, fast, self-contained application, with strong support for data-heavy interfaces. Makes the most sense if you need to talk to hardware or software that only ships a .NET/C# integration, or if your organisation already runs on .NET."

## What to ask

One focused round, not an interview. Prioritise these three; ask about the rest only if they'd change the answer:

- **What does the app do?** Especially: does it talk to hardware or local files, or is it mostly a window onto something remote?
- **What does the team already write?** This is the single heaviest factor. Ramp-up cost is real and usually dominates any technical advantage.
- **Who receives it?** Internal machines you control, or distributed outside the organisation? External distribution raises the stakes on download size, startup, antivirus friction, and protecting your own logic.

Secondary, when relevant:
- **Does lightness matter a lot?** (Small download, instant start, no installer friction.) This pushes away from Python-based even when nothing else does.
- **Is any of the logic genuinely sensitive?** Something that must not be easily read by whoever receives the app.
- **Might this later need a server with multiple clients?** Doesn't usually change today's answer, but worth surfacing early.
- **Is the team comfortable leaning on AI assistance for an unfamiliar stack?** If yes, an unfamiliar branch becomes more realistic — with one caveat noted under Rust below.

## Choosing a branch

**Python-based** when the team already writes Python, the app needs to reach local hardware, files or existing Python libraries, and it runs on machines you broadly control. Within it: **PySide6** for anything with real screens, tables, or live data; **tkinter** only for a genuinely tiny tool where any dependency at all feels like too much.

**Web-based** when the app should feel polished, or when small size and instant startup matter, or when the team is willing to invest in a compiled backend. This branch is often the right answer for tools distributed outside the organisation, even when the interface itself is simple.

**.NET-based** when a piece of hardware or software you must integrate with only ships a .NET/C# library, or the organisation already runs on .NET, and you want a small self-contained application. Note this genuinely competes with the web-based branch on size and startup — it is not the heavy runtime install it used to be.

**C++/Qt** only as a deliberate exception: an existing C/C++ codebase to link against directly, a hard real-time constraint, or a domain where Qt/C++ is already the established norm (automotive diagnostics tooling, for instance). Say plainly that no detailed skill covers it.

## Within the web-based branch: Rust or Go

Present both, don't decide silently. The interface side is identical either way — only the backend language and packaging tool differ.

| | Tauri + Rust | Wails + Go |
|---|---|---|
| Learning curve | Steeper. Rust's memory-ownership rules are a real climb — and notably the kind of friction AI assistance handles least reliably, so "AI will help us" discounts this less than it does elsewhere | Gentler. Closer to C in feel: static typing, explicit error returns, no ownership model, automatic memory management |
| Build speed | Noticeably slower. Rust does far more work at compile time; clean builds can run into minutes. Mitigable (`cargo check`, a faster linker, frontend-only changes skip Rust) but the gap stays | Fast by design — compilation speed was an explicit goal of the language. Usually seconds |
| Ecosystem | Larger community, more plugins, more prior art | Smaller but solid. v2 stable; v3 has a cleaner design but is still alpha |
| Shared types between interface and logic | Needs an added plugin | Built into the tool by default |
| Permission model | Explicit sandbox: you declare what the interface is allowed to do | None. Anything you expose is fully privileged, so what you expose *is* the security boundary |
| Mobile | Supported | Not supported |

If the team is closer to C, wants minimal new-language friction, and has no mobile ambitions, say that Wails is the lower-friction pick — but let the user confirm rather than deciding for them. Note that learning curve and build speed compound for a team still learning: more failed attempts, each costing a slower rebuild.

**If the user asks you to just pick one**, or says the choice has already been made organisation-wide, respect that and go straight to the matching skill. This choice may be locked in later as a standing decision; if the user says it has been, don't reopen it.

## Workflow: choosing a stack for a new project

1. **Tour the three branches briefly** in plain language, so the user sees options they may not know.
2. **Ask the three primary questions** above, plus any secondary ones that would change the answer.
3. **Recommend one branch**, stated plainly, with the reasoning tied to what the user told you — not a hedge across all three.
4. **If web-based**, present Rust vs Go using the table and let the user choose.
5. **Hand off explicitly** — see "Handing off to the specialized skill" below.
6. **If the answer is C++/Qt**, say plainly that no specialized skill exists and give a brief honest pointer instead of inventing detail.
7. **Don't re-litigate a settled choice.** If the user already named a stack, go straight to the matching skill.

## Workflow: auditing a single project's stack fit

Answers *"is this still the right stack?"* — not *"is this well-structured?"*. Hand off to the matching specialized skill for anything structural.

1. **Establish what changed** since the original choice, since a stack audit only makes sense against drift:
   - **Who receives it now**: was it internal and is now distributed externally (or vice versa)? Highest-impact change by far — it's what turns a mild packaging preference into a real exposure or antivirus-friction problem.
   - **What it does now**: meaningfully more or less local hardware/file access than when the stack was picked?
   - **Observed friction**: concrete symptoms — consistently slow development, recurring workarounds, bugs traceable to fighting the stack rather than the problem domain. Not a vague sense that something else might be nicer.
   - **Is it even in the tree**, or has it drifted to something adopted without ever being a deliberate choice?
2. **Give a verdict, not a list of considerations.** "The choice still holds" or "there's a real mismatch."
3. **If mismatched, weigh migration cost against staying**, explicitly. An audit that defaults to recommending a rewrite isn't a fair audit — staying on an imperfect stack is often correct once migration cost is priced honestly.
4. **If the choice holds**, say so and hand off to the matching skill for anything structural.

## Workflow: auditing a portfolio for stack sprawl

The one angle no single-project skill can see.

1. **Inventory the stacks** across the tools the user names.
2. **Check for sprawl**: similar problems solved on different, unjustified stacks. Every additional stack compounds maintenance cost across the whole team, not just its owner — flag it even if each individual choice was locally reasonable at the time.
3. **Distinguish justified diversity from drift.** The three branches exist because they genuinely serve different needs; using two or three of them deliberately is not sprawl. A tool sitting on something outside the tree without ever having been a deliberate exception is.
4. **Recommend consolidation only where it's cheap enough to be worth it.** Don't recommend rewriting a working tool for tidiness alone.

## Handing off to the specialized skill

This skill lives in the `process-light` block, so it's present from a
project's very first sync — before `pyproject.toml`, `Cargo.toml`, `go.mod` or
a `.csproj` exists. The specialized skills live in their **stack blocks**,
which stack detection can't suggest yet at that point. So the handoff is
explicit: naming the skill isn't enough, the block has to be synced first.

Once a branch is chosen, tell the user which block to sync and give the exact
command:

| Branch | Block | Skill it brings |
| --- | --- | --- |
| Python | `tech-stack-python` | `python-desktop-architecture` |
| Web-based + Rust | `tech-stack-rust` | `rust-webview-desktop-architecture` |
| Web-based + Go | `tech-stack-go` | `go-webview-desktop-architecture` |
| .NET | `tech-stack-dotnet` | `dotnet-desktop-architecture` |

```
toolkit-sync sync <block-id> --toolkit-root <root> --project-dir .
```

`<root>` is the toolkit checkout the drift-check hook prints at the start of
every session ("using toolkit checkout at ..."), `~/.cache/ai-dev-toolkit` by
default. After the sync, the specialized skill is available and takes over.

**Route, never duplicate.** Don't answer the structural question yourself
while waiting for the sync — folder layout, packaging, the logic/interface
boundary all belong to the specialized skill. If the user declines to sync,
say plainly which guidance they're doing without.
