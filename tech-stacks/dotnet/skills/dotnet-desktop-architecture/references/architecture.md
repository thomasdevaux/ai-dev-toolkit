# Reference — .NET / Avalonia Desktop Architecture

Solution layout, MVVM conventions, publishing detail, audit checklist.

**Contents**
1. Solution and folder layout
2. MVVM conventions
3. Publishing in detail
3b. Where the app writes at runtime
4. Anti-patterns — audit checklist
5. Prompts (standalone use)
6. Evolving toward a server with remote clients

---

## 1. Solution and folder layout

```text
MyApp/
├── src/
│   ├── MyApp.Core/                  # framework-free: NO Avalonia references
│   │   ├── Models/
│   │   ├── Services/                # business logic, hardware/file/network access
│   │   ├── Abstractions/            # interfaces the app depends on
│   │   └── MyApp.Core.csproj
│   │
│   └── MyApp.Desktop/               # the Avalonia application
│       ├── Views/                   # .axaml + minimal code-behind
│       │   ├── MainWindow.axaml
│       │   └── MainWindow.axaml.cs
│       ├── ViewModels/              # orchestration, binds Views to Core
│       │   ├── ViewModelBase.cs
│       │   └── MainWindowViewModel.cs
│       ├── Services/                # app-level only: dialogs, navigation, theming
│       ├── Assets/
│       ├── App.axaml
│       ├── Program.cs               # entry point, DI container setup
│       └── MyApp.Desktop.csproj
│
├── tests/
│   └── MyApp.Core.Tests/            # tests Core with no UI involved
│
├── Directory.Build.props            # AOT + trimming config, inherited by all projects
├── Directory.Packages.props         # package versions, centralized for the whole solution
├── MyApp.sln
└── README.md
```

**`Directory.Packages.props`** — central package management, on from the start.
The solution is multi-project by construction (Core, Desktop, tests, plus a CLI
or server later), and without it every `.csproj` carries its own version
numbers, which drift apart silently. That drift bites hardest under Native AOT,
where whether a package is AOT-compatible depends on the exact version:

```xml
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Avalonia" Version="…" />
    <PackageVersion Include="CommunityToolkit.Mvvm" Version="…" />
  </ItemGroup>
</Project>
```

Individual projects then reference packages without a version:
`<PackageReference Include="CommunityToolkit.Mvvm" />`.

**The rule that matters**: `MyApp.Core` has no reference to Avalonia, and never will. It's testable without a UI, and reusable by a console tool or a server if one ever appears. If a `using Avalonia` appears in Core, the separation has broken regardless of folder names.

**Adding a second consumer later** — a CLI or a server sharing the same logic — means adding a project alongside the desktop app:

```text
src/
├── MyApp.Core/                   # unchanged, referenced by both
├── MyApp.Desktop/                # Avalonia app
└── MyApp.Cli/                    # or MyApp.Server — the second consumer
    ├── Program.cs
    └── MyApp.Cli.csproj
```

Neither app references the other; both reference Core. This is genuinely cheap in .NET **provided the rule above held from the start** — Core free of Avalonia, and no shared logic quietly accumulated inside the Desktop project. In practice the migration cost is almost entirely in step 3 of the reuse workflow: pulling back the convenience code that drifted into the app project. See §6 for the distinct case of a server serving remote clients.

---

## 2. MVVM conventions

**Views** (`.axaml` + code-behind): display and layout only. Code-behind should be close to empty — a constructor calling `InitializeComponent()`, and occasionally view-specific visual handling that genuinely cannot be expressed in XAML. No business logic, no service calls.

**View models**: orchestration. They call into `MyApp.Core` services, expose properties for binding, and expose commands for user actions. They should be testable without instantiating any view.

**Models and services** live in `MyApp.Core`, framework-free.

**Use CommunityToolkit.Mvvm** rather than hand-writing `INotifyPropertyChanged`:

```csharp
public partial class MainWindowViewModel : ViewModelBase
{
    private readonly IDeviceService _devices;

    public MainWindowViewModel(IDeviceService devices) => _devices = devices;

    [ObservableProperty]
    private string _status = "Idle";

    [RelayCommand]
    private async Task ConnectAsync()
    {
        Status = "Connecting…";
        await _devices.ConnectAsync();
        Status = "Connected";
    }
}
```

The source generators produce the property-change plumbing at compile time, which keeps the code short **and** is AOT-friendly — unlike reflection-based MVVM frameworks, which are exactly what causes trouble under Native AOT.

**Dependency injection**: register `MyApp.Core` services in the container in `Program.cs`, and inject them into view models through constructors. View models should never construct their own service dependencies — that couples them to concrete implementations and blocks testing.

**Every view needs a public parameterless constructor.** This is not just convention: XAML resource resolution fails at runtime under AOT without it.

---

## 3. Publishing in detail

### Native AOT — the default

`Directory.Build.props` at the solution root, so every project inherits it and Debug builds stay untouched:

```xml
<Project>
  <PropertyGroup Condition="'$(Configuration)' == 'Release'">
    <PublishAot>true</PublishAot>
    <InvariantGlobalization>true</InvariantGlobalization>
    <StripSymbols>true</StripSymbols>
  </PropertyGroup>
</Project>
```

Publish:

```bash
dotnet publish src/MyApp.Desktop -c Release -r win-x64 -o dist/release
```

For local debugging, route the ordinary build output to `dist/debug/` the same way — `dotnet build` supports `-o` directly, and AOT never applies to a Debug configuration:

```bash
dotnet build src/MyApp.Desktop -c Debug -o dist/debug
```

Result: a native executable requiring no .NET runtime on the user's machine, starting fast because there's no just-in-time compilation at launch.

**Making Avalonia and AOT coexist** — the friction points, in the order they usually bite:

1. **Views without public parameterless constructors** → XAML resources fail to resolve at runtime. Fix every view.
2. **Trimming removes assemblies that binding needs** → add `TrimmerRootAssembly` entries for the assemblies involved.
3. **XAML files not marked as `AvaloniaResource`** → they won't be found.
4. **Third-party controls that use reflection** → may not be AOT-compatible at all. Check before adopting one; this is the failure mode with no easy workaround.

**Always test the published binary**, not just the Debug run. AOT failures appear only in the published output, and often only on a machine other than the developer's.

### Self-contained without AOT — the honest fallback

```bash
dotnet publish src/MyApp.Desktop -c Release -r win-x64 -o dist/release \
  --self-contained true -p:PublishSingleFile=true
```

Still no runtime install required, still a single file. Larger and slower to start than AOT, but it works when a dependency can't be made AOT-compatible. Choosing this because a required control doesn't support AOT is a legitimate engineering decision, not a failure — document why.

### Framework-dependent — internal fleets only

Smallest output, but the correct .NET runtime must already be installed. Acceptable only where you control the machines. Never for external distribution.

### Signing

Sign anything distributed outside the organisation. It establishes publisher identity and avoids SmartScreen warnings. It does not protect the code.

---

## 3b. Where the app writes at runtime

Distinct from where the code lives: where the installed application writes
settings, its database, and its logs. Writing beside the executable works
throughout development and breaks the day the app is installed under
`Program Files`, where the process has no write access — so it surfaces at the
user's site, not on the developer's machine.

Use `Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData)` and
put everything under a `<Vendor>/<AppName>/` subfolder of it. The path belongs
in `MyApp.Core` behind a small abstraction, not hard-coded at each call site —
that keeps it testable and keeps `MyApp.Cli` or a future server from inheriting
a desktop-shaped assumption about where state lives.

---

## 4. Anti-patterns — audit checklist

| # | Symptom | Diagnosis |
|---|---|---|
| 1 | Business logic in code-behind or in a view | Logic leaked into the interface layer; untestable, unreusable |
| 2 | `using Avalonia` inside the Core library | Framework-free separation broken |
| 3 | View models constructing their own services | No dependency injection; untestable in isolation |
| 4 | `.Result` or `.Wait()` on a Task in UI code | Classic deadlock source in UI applications |
| 5 | Blocking work on the UI thread instead of `await` | Freezes the interface |
| 6 | Hand-written `INotifyPropertyChanged` boilerplate everywhere | CommunityToolkit source generators do this better and AOT-friendly |
| 7 | `PublishAot` set but the published binary never tested | AOT failures surface only in published output |
| 8 | View without a public parameterless constructor | Breaks XAML resolution under AOT |
| 9 | Third-party control adopted without checking AOT compatibility | May force an unplanned fallback late |
| 10 | Framework-dependent publish shipped externally | Users need the right runtime installed; predictable support burden |
| 11 | Externally distributed and unsigned | SmartScreen friction |
| 12 | No tests exercising Core without the UI | Confirms the separation was never real |
| 13 | Reflection-based MVVM framework combined with AOT ambitions | Fundamentally at odds; pick one |
| 14 | Shared logic accumulating in MyApp.Desktop instead of MyApp.Core | Blocks adding a second consumer cheaply; the usual hidden migration cost |
| 15 | Core public methods passing live handles or streaming objects | Blocks any later move to a network boundary (§6) |
| 16 | Package versions duplicated across `.csproj` files | They drift apart silently; under AOT, compatibility depends on the exact version (§1) |
| 17 | Writes configuration, database or logs beside the executable | Breaks on any read-only or per-machine install; surfaces only after deployment (§3b) |

---

## 5. Prompts (standalone use)

**New project**
```
Set up a new Avalonia desktop solution: a framework-free MyApp.Core class library,
a MyApp.Desktop Avalonia app using CommunityToolkit.Mvvm, dependency injection into
view models, and Directory.Build.props configured for Native AOT on Release.
Ask me first: who receives this app, whether any third-party controls are planned,
and whether startup time or download size matters.
```

**Audit**
```
Audit this Avalonia project:
1. Is there business logic in views or code-behind?
2. Does the Core library reference Avalonia anywhere?
3. If AOT is configured, is it actually viable — views with public parameterless
   constructors, trimmer roots, AOT-compatible third-party controls?
4. Any .Result / .Wait() or blocking calls on the UI thread?
5. Does the publishing mode match who actually receives this?
Rank by user-visible impact first. Evidence with file and line.
```

**Publishing decision**
```
Help me decide how to publish this app. Ask about: who receives it, whether the
.NET runtime can be assumed present, whether startup and download size matter,
and which third-party controls are in use.
Then recommend AOT, self-contained, or framework-dependent, with the concrete
command and any configuration needed — and say plainly if AOT isn't viable here.
```

---

## 6. Evolving toward a server with remote clients

Distinct from adding a CLI (§1): there the second consumer runs on the same machine, here it serves remote clients over a network. Three points, none covered by N1–N6.

### 1. Not everything in Core can move to a server

If this branch was chosen because a vendor SDK only ships a .NET library — a common reason to be here — that SDK almost certainly talks to hardware attached to the client machine. A remote server cannot reach it. Classify module by module:

- **Centralizable** — becomes real server-side state, shared across clients.
- **Inherently local** — stays client-side. The desktop app becomes one client among several, calling the server for shared concerns while keeping device access local.

This is a product decision. Assuming all of Core centralizes is the standard way this goes wrong.

### 2. Design Core's public surface as if it were already a network API

Methods taking and returning plain serializable types map cleanly onto endpoints. Methods passing live handles, open device connections, or streaming objects do not, and must be redesigned before anything can be exposed remotely.

A useful test: could this method's arguments and return value survive being serialized to JSON and deserialized on the other side? If not, it isn't endpoint-ready.

Keeping Core free of Avalonia types (N1) covers part of this; the remaining discipline is avoiding stateful handles in public signatures.

### 3. Multi-user authentication and data isolation are unaddressed

A desktop application implicitly trusts whoever is at the keyboard. A server cannot. Nothing in the desktop design says which remote user may read or modify which data — authentication, session handling, and isolation between clients need their own design pass on the server side, not treated as a byproduct of moving Core behind a network boundary.
