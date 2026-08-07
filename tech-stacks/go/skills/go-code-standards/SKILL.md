---
name: go-code-standards
description: Set up or repair the team's Go quality tooling in a module - gofumpt, golangci-lint, and the shared .golangci.yml they read. Use when a Go project has no .golangci.yml, has one that diverges from the team's or is still on the v1 schema, when adopting the standards on an existing module with a backlog of findings, or when deciding whether a linter is worth enabling.
---

# Go Code Standards

Install the team's Go lint configuration in a module, or bring an existing
one back in line. The day-to-day rules — run the tools, how to write a
legitimate `//nolint` — live in `rules/style.md` and load on their own; this
skill is the setup procedure.

## The stack, and why

| Job | Tool |
|---|---|
| Format | `golangci-lint fmt` (gofumpt + goimports) |
| Lint | `golangci-lint run` |
| Test | `go test ./...` |

**golangci-lint v2 split formatters from linters.** `formatters:` and
`linters:` are separate top-level keys, and a v1 config file is not accepted.
An existing project on v1 is migrated with `golangci-lint migrate`, not by
hand.

**gofumpt over plain gofmt.** It is gofmt plus a set of small extra rules,
and its output is always valid gofmt output — so nothing downstream notices,
and a category of review comments disappears.

**`enable-all` is not used.** It opts the project into every linter a future
release adds, which turns a routine upgrade into an unplanned lint-fixing
session. The reference enables a named set; growing that set is a decision
someone makes.

## Procedure

### A module with no configuration

1. Copy `references/.golangci.yml` to the module root.
2. Replace the `goimports.local-prefixes` placeholder with the module path
   from `go.mod`. Left as-is, import grouping silently does nothing useful.
3. Decide on `revive`'s `exported` rule: keep it for a library whose
   identifiers other modules import, disable it for an application module
   where nothing is.
4. Copy `references/editorconfig.ini` to the module root as `.editorconfig`
   if there is none. It is the same baseline in every stack, and its `[*.go]`
   section states the tab indentation gofmt is not going to negotiate about.
5. Run `golangci-lint fmt`, and commit that as one mechanical commit,
   separate from any behaviour change.
6. Run `golangci-lint run` and deal with the output per the section below.

### A module that already has a configuration

Do not overwrite it. First check the schema: no `version: "2"` key means it
is a v1 file — run `golangci-lint migrate` and review the result before
comparing anything.

Then diff against the reference and report the differences, grouped:

- **Linters the project disables that the reference enables** — ask why
  before removing the exception. `errcheck` disabled wholesale is the common
  one, and usually means a backlog rather than a decision.
- **Linters the project enables that the reference does not** — a candidate
  to propose upstream, not to delete.
- **Broad `exclusions`** — a path exclusion covering most of the source tree
  is a backlog recorded as permanent.

Record deliberate differences as comments in the file next to the setting.

### Adopting on an existing module with a backlog

The failure mode is a first run reporting several hundred findings, which
gets ignored wholesale and the standard dies on day one. Instead:

1. Land `golangci-lint fmt` first, alone, as one mechanical commit.
2. Clear the default linters (errcheck, govet, ineffassign, staticcheck,
   unused) before adding any of the reference's extras. They are the ones
   that find real bugs.
3. Add the extras in small batches, each one clean before the next.
   `errorlint` and `contextcheck` tend to produce the most work, because
   fixing them changes signatures.
4. Never adopt by adding a repo-wide exclusion, and never by disabling
   `nolintlint` — those are the two moves that make the backlog permanent.

## Changing the standard

The reference configuration is the team's, not the module's. A linter worth
enabling everywhere is changed in
`tech-stacks/go/skills/go-code-standards/references/` in the toolkit
checkout, and reaches projects at their next sync. Editing one module's
`.golangci.yml` to win an argument is how four modules end up with four
standards.
