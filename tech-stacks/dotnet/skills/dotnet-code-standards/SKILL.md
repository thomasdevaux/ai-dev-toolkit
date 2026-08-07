---
name: dotnet-code-standards
description: Set up or repair the team's .NET quality tooling in a solution - Directory.Build.props, .editorconfig analyzer severities, nullable reference types, and dotnet format. Use when a .NET solution has no shared analyzer configuration, has one that diverges from the team's, when adopting the standards on an existing codebase with a backlog of warnings, or when deciding whether an analyzer rule is worth enforcing.
---

# .NET Code Standards

Install the team's .NET quality configuration in a solution, or bring an
existing one back in line. The day-to-day rules — nullable discipline, async
discipline, how to suppress a warning legitimately — live in `rules/style.md`
and load on their own; this skill is the setup procedure.

## The stack, and why

| Job | Tool |
|---|---|
| Format | `dotnet format` |
| Analyze | the .NET analyzers, during `dotnet build` |
| Configure | `Directory.Build.props` + `.editorconfig` |

**Nothing to install.** The analyzers ship with the SDK and are on by default
for net5.0+. What is *not* on by default is the part that matters:
`AnalysisMode`, `EnforceCodeStyleInBuild`, and `TreatWarningsAsErrors`. A
solution with an `.editorconfig` and none of those has style rules that are
IDE-only suggestions — which is the usual reason a team "has a standard" and
still drifts.

**`Directory.Build.props` at the solution root, not per-`.csproj`.** MSBuild
walks up from each project directory and applies the first one it finds, so a
single file covers the tree and a new project inherits it with nothing added.

**`AnalysisMode = Recommended`, not `All`.** `All` enables globalization and
some design rules that produce mostly noise in application code. It earns its
keep in a library with consumers outside the team; say so in a comment when
turning it up.

## Procedure

### A solution with no configuration

1. Copy `references/Directory.Build.props` to the solution root and set
   `TargetFramework` to what the solution actually targets.
2. Build the solution root's `.editorconfig` from two references, in this
   order: `references/editorconfig.ini` (the cross-stack baseline — encoding,
   line endings, indentation) then `references/editorconfig-csharp.ini` (the
   C# style and analyzer severities). They do not overlap. The `.ini`
   extension on both exists only so the files stay inert inside the toolkit
   checkout — the destination filename is `.editorconfig`.
3. Decide on `CA2007` (`ConfigureAwait(false)`): keep it a warning in library
   code, set it to `none` in an application with no synchronization context.
4. Run `dotnet format`, and commit that as one mechanical commit, separate
   from any behaviour change.
5. Run `dotnet build` and deal with the output per the section below.

### A solution that already has a configuration

Do not overwrite it. Diff against the references and report the differences,
grouped:

- **`Nullable` disabled** — the highest-value divergence to close, and the
  most work. Treat it as its own project, per the section below.
- **`TreatWarningsAsErrors` off, or `EnforceCodeStyleInBuild` absent** —
  usually not a decision, just never set. These are what make the rest real.
- **`NoWarn` lists in `.csproj` files** — each entry is a suppression with no
  recorded reason. Enumerate them and ask; most turn out to be one old
  finding that was never fixed.
- **Rules the solution enforces that the reference does not** — a candidate
  to propose upstream, not to delete.

Record deliberate differences as comments next to the setting.

### Adopting on an existing solution with a backlog

The failure mode is a first build reporting several hundred warnings, which
gets ignored wholesale and the standard dies on day one. Instead:

1. Land `dotnet format` first, alone, as one mechanical commit.
2. Add `Directory.Build.props` with `TreatWarningsAsErrors` **off**, so the
   build still passes and the warning count becomes visible.
3. Clear the analyzer warnings in batches by rule id, one commit each.
4. Enable nullable per project, not solution-wide: `<Nullable>enable</Nullable>`
   in one `.csproj`, clear it, move on. Solution-wide on day one produces a
   warning count nobody will work through.
5. Turn `TreatWarningsAsErrors` on last, once the count is zero. Doing it
   first just means someone adds `NoWarn` to get their build back.

## Changing the standard

The reference configuration is the team's, not the solution's. A rule worth
enforcing everywhere is changed in
`tech-stacks/dotnet/skills/dotnet-code-standards/references/` in the toolkit
checkout, and reaches projects at their next sync. Editing one solution's
`.editorconfig` to win an argument is how four solutions end up with four
standards.
