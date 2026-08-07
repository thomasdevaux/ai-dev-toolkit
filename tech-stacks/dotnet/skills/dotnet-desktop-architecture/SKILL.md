---
name: dotnet-desktop-architecture
description: Choose, scaffold, and audit the architecture of a .NET desktop app built with Avalonia (C# + XAML). Use when building, structuring or reviewing one — MVVM and project layout, publishing and distribution (Native AOT, trimming, self-contained dotnet publish), or integrating a vendor SDK that ships only a .NET/C# library. Assumes the .NET branch is already chosen; if no stack has been settled on, use desktop-app-architecture first.
---

# .NET / Avalonia Desktop Architecture

Pick an architecture and a publishing strategy for an Avalonia desktop app, scaffold it, or audit an existing one.

## Scope

Covers the .NET branch: **Avalonia** for the interface (XAML + MVVM), **C#/.NET** for the logic, and `dotnet publish` for shipping.

Avalonia is MIT-licensed with no usage restrictions, mature (first released 2013), and used in production by organisations including JetBrains, Autodesk and Schneider Electric. Unlike WPF, it runs on Windows, macOS and Linux — it draws its own interface with Skia rather than wrapping each platform's native controls, so the result looks identical everywhere. It's widely described as the spiritual successor to WPF, so WPF or WinUI experience transfers directly.

If the user hasn't settled on the .NET branch, defer to `desktop-app-architecture`.

## When this branch is the right one

Worth restating so it doesn't get chosen by default: the strongest reasons to be here are **a vendor SDK that only ships a .NET/C# library**, **an organisation already running on .NET**, or **existing WPF code or XAML skills to build on**. Avalonia competes well on size and startup with the web-based branch — but if none of those reasons apply, the choice deserves a second look.

## Core idea

Two decisions carry disproportionate weight.

- **Keeping logic out of the views.** Business logic belongs in plain C# classes with no Avalonia types anywhere near them. In MVVM terms: models and services stay framework-free, view models orchestrate, views only display. Beyond the usual testability argument, this has a specific payoff here — a framework-free class library is what lets the same logic be reused by a console tool or a server later.
- **Deciding how you publish, early.** Native AOT produces a small, fast, self-contained executable, but it constrains how you write code. Retrofitting it onto a finished app that leans on reflection is significantly harder than building with it in mind. Decide at the start, not at release.

## Two structural states

There's no profile spectrum here, unlike the web-based branch. With a single language and no technical boundary between interface and logic (XAML is not comparable to a cross-language IPC boundary), the structural question is binary:

- **Application-only** (default) — `MyApp.Core` is a class library referenced by the desktop app alone. Right for almost every tool.
- **Reusable logic** — a second consumer sits alongside the app: `MyApp.Cli`, `MyApp.Server`, a scheduled job. Only move here when that consumer actually exists.

**If that second consumer is a CLI companion to the desktop app, there are two ways to build it — never default, always ask which one fits:**

| | Single project, dual-mode | Separate `MyApp.Cli` project |
|---|---|---|
| What ships | One executable — runs as CLI with arguments, opens the window with none | Two executables |
| CLI weight | Avalonia is still referenced by the same project, and its static setup may run before argument checking depending on how startup is structured | Lean — `MyApp.Cli` has no Avalonia reference at all |
| Guarantee against interface code leaking into CLI logic | None but discipline | Enforced by the project reference graph — `MyApp.Cli` can't compile against Avalonia-only types |
| Fits best | Occasional CLI use, simplest solution structure | CLI invoked repeatedly in scripts or CI, or where a compiler-enforced boundary matters |

Dual-mode is honestly a bit less clean in Avalonia than in Tauri or Wails: check arguments in `Program.cs` before calling `BuildAvaloniaApp().StartWithClassicDesktopLifetime(args)`, but be aware some of Avalonia's static initialization can still run first depending on how the entry point is structured — verify no window flashes or GPU/windowing setup happens on the pure-CLI path before recommending this option for a case where that matters. Given .NET solutions are already cheap to extend with a new project, the separate-project option carries less overhead here than the equivalent choice in Rust or Go — lean more readily toward it when in doubt.

The good news for this branch: because .NET solutions are already multi-project by convention, `MyApp.Core` is a separate assembly from day one. Adding a second consumer is genuinely just a new project referencing it — provided the rule below held.

## The six decisions

| # | Decision | Default |
|---|---|---|
| N1 | Where does business logic live? | A separate framework-free class library, referenced by the app |
| N2 | Interface pattern | MVVM with CommunityToolkit.Mvvm (source generators, avoids hand-written boilerplate) |
| N3 | Publishing mode | Native AOT self-contained, with a documented fallback (see below) |
| N4 | Background work | `async`/`await` throughout; `Task.Run` for CPU-bound work; never block the UI thread |
| N5 | Error handling | Global handler on unhandled exceptions, user-facing messages separate from logged detail |
| N6 | Dependency injection | Constructor injection into view models via a container, rather than view models constructing their own dependencies |

N1 and N3 are the ones worth real time.

## Publishing: the decision that shapes the code

**Default — Native AOT, self-contained:**

```bash
dotnet publish -c Release -r win-x64 -p:PublishAot=true
```

Compiles ahead of time to a native binary. No .NET runtime needs to be installed on the user's machine, startup is fast because there's no just-in-time compilation, and the result is substantially smaller than a traditional self-contained build. Microsoft's own reported figures for a comparable desktop app show roughly half the startup time and a several-fold reduction in package size.

**What it costs, stated plainly.** Native AOT assumes everything reachable is known at build time. Avalonia's XAML binding uses reflection, so the two need reconciling:

- Every view needs a public parameterless constructor, or XAML resources fail to resolve at runtime.
- Assemblies that binding depends on must be protected from trimming via `TrimmerRootAssembly`.
- Some third-party Avalonia controls are not AOT-compatible — verify before depending on one.
- Builds take longer, since this is real compilation rather than packaging.

A practical convention: put the AOT configuration in a single `Directory.Build.props` at the solution root so every project inherits it, rather than scattering settings across `.csproj` files. Debug builds stay unaffected; AOT applies only on release publish.

**Fallback — self-contained without AOT**, when a required dependency can't be made AOT-compatible:

```bash
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true
```

Still requires no runtime installed, still a single file, but larger and slower to start than AOT. This is the honest fallback — not a failure.

**Framework-dependent** (smallest output, but requires the correct .NET runtime already installed) is only appropriate for internal fleets where you control the machines. Don't use it for anything distributed externally.

**Code signing**: as with any externally distributed desktop app, sign the executable. It doesn't protect the code, but it establishes publisher identity and avoids SmartScreen warnings.

## Note on protecting logic

.NET assemblies compiled normally are straightforward to decompile — tools like ILSpy recover very readable C#. **Native AOT changes this substantially**, since the output is a real native binary with no intermediate language to recover, which is a genuine advantage of this branch over a normal .NET build. It's still not absolute against a determined attacker with a disassembler. If some logic truly must not leave your control, the answer is the same as in any branch: keep it on a server you control, when the app can reach one.

## Workflow: scaffolding a new project

1. **Confirm why this branch was chosen** — vendor SDK, existing .NET environment, or existing XAML skills. If none apply, it's worth a brief check that `desktop-app-architecture` was run.
2. **Ask about publishing stakes before assuming**: who receives this, does startup or download size matter, are there third-party controls in mind that might not survive AOT? This sets N3.
3. **Read `references/architecture.md`** for the solution layout and full publishing detail.
4. **Create the framework-free class library first**, before any view. Everything else references it; nothing in it references Avalonia.
5. **Use CommunityToolkit.Mvvm** rather than hand-rolling `INotifyPropertyChanged` — its source generators remove most of the boilerplate and are AOT-friendly.
6. **Set up AOT configuration at the start** via `Directory.Build.props`, even if the first release is far off. Retrofitting is the expensive path.
7. **Wire a global unhandled-exception handler** from the start.
8. **Generate nothing tied to a forge or CI system.**
9. **Document N1–N6 in the project README.**

## Workflow: auditing an existing project

1. **Read `references/architecture.md`** (anti-pattern checklist).
2. **Check whether business logic sits in views or code-behind** — the equivalent of the leaked-logic problem in every other branch, and the most consequential finding here.
3. **Check AOT compatibility honestly** if AOT is claimed: reflection-heavy binding, third-party controls, missing trimmer roots. An app configured for AOT that silently falls back or crashes at runtime is worse than one that never claimed it.
4. **Check the publishing mode against who actually receives the app** — framework-dependent output shipped externally is a real finding.
5. **Check async discipline**: blocking calls on the UI thread, `.Result` or `.Wait()` on tasks (a classic deadlock source in UI applications).
6. **Rank by user-visible impact first**, then structural debt.
7. **Modify no files** unless asked.

## Workflow: moving to reusable logic

When a real second consumer appears (a CLI, a scheduled job, a server):

1. **Check the prerequisite**: does `MyApp.Core` reference Avalonia anywhere, directly or transitively? If yes, break that first — it's what makes the rest cheap or expensive.
2. **Add the new project** (`MyApp.Cli`, `MyApp.Server`) referencing `MyApp.Core`. Neither app references the other.
3. **Move anything shared that currently lives in the desktop project** down into Core — this is usually where the real work is, since convenience code accumulates in the app project.
4. **Justify it by the consumer that exists**, not the one that might.

## Workflow: evolving toward a server with remote clients

Different from reuse on one machine. Three points, none covered by N1–N6:

1. **Not everything in `MyApp.Core` can move to a server.** If this branch was chosen for a vendor SDK talking to local hardware, that part is inherently client-side — a remote server can't reach a client's device. Classify module by module: centralizable (real server-side state) versus inherently local (stays client-side, the desktop app becoming one client among several). A product decision, not a mechanical refactor.
2. **Design Core's public surface as if it were already a network API.** Methods taking and returning plain serializable types convert cleanly into endpoints; methods passing live handles, open connections, or streaming objects don't. A useful test: could the arguments and return value survive a round trip through JSON?
3. **Multi-user authentication and data isolation are a separate, unaddressed problem.** A desktop app implicitly trusts whoever is at the keyboard; a server cannot. Authentication, sessions, and isolation between clients need their own design pass.

## Reference file

`references/architecture.md` — solution and folder layout, MVVM conventions, publishing configuration in full, and the anti-pattern checklist.
