---
paths:
  - "**/*.go"
---

# Go code standards

The mechanical part is enforced by tooling, not by this file: `gofumpt` for
formatting, `golangci-lint` for lint. Their configuration is the actual
standard — `go-code-standards` holds the ready-to-copy version and the
procedure for adopting it. If a module has no `.golangci.yml` yet, say so
once and offer to run that skill.

What tooling cannot decide, and this file does:

- **Run the tools before handing work back.** `golangci-lint fmt`, then
  `golangci-lint run`, then `go test ./...`. A finding is either fixed or
  silenced with a reason — never left reported.
- **Silencing needs a named linter and a why.** `//nolint:errcheck` alone is
  not acceptable; `//nolint:errcheck // best-effort close on a read-only
  file` is. `golangci-lint` is configured to reject the bare form.
- **Every error is handled or deliberately dropped.** Dropping is written
  `_ = f()` with a comment, never an ignored return value. An error crossing
  a package boundary is wrapped with context: `fmt.Errorf("reading config:
  %w", err)`. The `%w` verb, not `%v` — `%v` breaks `errors.Is` and
  `errors.As` for every caller downstream.
- **Return errors, don't panic.** `panic` is for genuinely unrecoverable
  programmer error at startup. A library that panics has taken the decision
  away from its caller.
- **Accept interfaces, return concrete types.** And define the interface in
  the consuming package, not alongside the implementation — that is what
  keeps the dependency pointing the right way.
- **`context.Context` is the first parameter** of anything that does I/O,
  blocks, or calls something that does. It is never stored in a struct.
- **Goroutines have an owner and an exit.** Whoever starts one knows how it
  stops — a context, a closed channel, a `WaitGroup`. A goroutine with no
  stated exit path is a leak that has not been noticed yet.
- **Name things for the caller's vocabulary, and keep it short.** Package
  name plus type name reads as one phrase: `http.Client`, not
  `http.HTTPClient`. Single-letter receivers are idiomatic here, not sloppy.

Adding a linter to the shared configuration is a team decision, not a
per-module one: propose it against the toolkit's `go-code-standards`
reference rather than editing one module's `.golangci.yml` alone.
