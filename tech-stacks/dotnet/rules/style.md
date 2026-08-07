---
paths:
  - "**/*.cs"
---

# C# code standards

The mechanical part is enforced by the build, not by this file: the .NET
analyzers run during compilation, configured by `Directory.Build.props` and
`.editorconfig`. That configuration is the actual standard —
`dotnet-code-standards` holds the ready-to-copy version and the procedure for
adopting it. If a solution has no `Directory.Build.props` yet, say so once and
offer to run that skill.

What tooling cannot decide, and this file does:

- **A build with warnings is a failing build.** The shared configuration sets
  `TreatWarningsAsErrors`, so this is enforced rather than asked for. Run
  `dotnet format --verify-no-changes` and `dotnet build` before handing work
  back.
- **Suppressing needs a rule id and a why.** `#pragma warning disable CA1031`
  alone is not acceptable; the same line with a comment saying what makes it
  the right call, and a matching `restore` scoped as tightly as possible, is.
  A blanket `NoWarn` in a `.csproj` is not acceptable.
- **Nullable reference types stay enabled.** `<Nullable>enable</Nullable>` is
  in the shared props and is not turned off per project. The null-forgiving
  operator `!` is a claim about an invariant — it carries a comment stating
  it, or it is a bug waiting.
- **`async` all the way down.** No `.Result`, no `.Wait()`, no
  `.GetAwaiter().GetResult()` outside `Main`. Every async method that does
  I/O takes a `CancellationToken` and passes it on. Library code awaits with
  `.ConfigureAwait(false)`.
- **Catch what you can act on.** `catch (Exception)` belongs at a genuine
  boundary — a request handler, a top-level worker loop, a UI event — and
  carries a comment saying so. `throw ex;` resets the stack trace; use
  `throw;` or wrap in a new exception with the original as `innerException`.
- **`IDisposable` is honoured.** Anything disposable is in a `using`
  declaration or owned by a type that disposes it. A field holding a
  disposable makes its owner disposable too.
- **Prefer the type system over convention.** `record` for value-like data,
  `required` for what a constructor cannot default, an enum or a closed
  hierarchy over a magic string.

Adding an analyzer rule to the shared configuration is a team decision, not a
per-solution one: propose it against the toolkit's `dotnet-code-standards`
reference rather than editing one solution's `.editorconfig` alone.
