---
name: rust-code-standards
description: Set up or repair the team's Rust quality tooling in a crate or workspace - rustfmt, clippy, and the shared [lints] configuration they read. Use when a Rust project has no [lints] table, has one that diverges from the team's, when adopting the standards on an existing crate with a backlog of warnings, or when deciding whether a clippy lint is worth denying.
---

# Rust Code Standards

Install the team's Rust lint configuration in a crate or workspace, or bring
an existing one back in line. The day-to-day rules — run the tools, how to
allow a lint legitimately — live in `rules/style.md` and load on their own;
this skill is the setup procedure.

## The stack, and why

| Job | Tool |
|---|---|
| Format | `cargo fmt` |
| Lint | `cargo clippy --all-targets -- -D warnings` |
| Test | `cargo test` |

**Configuration lives in `Cargo.toml`, not in crate-root attributes.** The
`[lints]` table (Cargo 1.74+) is the current mechanism: one place, inherited
by every target, visible to anyone reading the manifest. Crate-root
`#![deny(...)]` blocks and `RUSTFLAGS` in CI both predate it and both hide
the configuration from the person looking for it.

**`--all-targets` is not optional.** Without it, clippy skips tests,
benchmarks and examples — which is exactly where the sloppy code
accumulates.

**rustfmt stays near-default on purpose.** Its value is that every Rust
codebase looks the same; a project with an opinionated `rustfmt.toml` has
traded that away for preferences. Pin the edition, stop there.

## Procedure

### A workspace or crate with no configuration

1. Read `references/Cargo-lints.toml`. Merge the `[workspace.lints.rust]`
   and `[workspace.lints.clippy]` tables into the workspace root's
   `Cargo.toml` — or, for a single-crate project, the same tables without the
   `workspace.` prefix.
2. In each member crate, add:
   ```toml
   [lints]
   workspace = true
   ```
   A member without this line inherits nothing — that is the usual reason a
   workspace "has lints configured" and one crate still fails review.
3. Create `rustfmt.toml` at the project root with the edition pinned.
4. Copy `references/editorconfig.ini` to the project root as `.editorconfig`
   if there is none. It is the same baseline in every stack and settles what
   an editor decides before any formatter runs.
5. Run `cargo fmt`, and commit that as one mechanical commit, separate from
   any behaviour change.
6. Run `cargo clippy --all-targets -- -D warnings` and deal with the output
   per the section below.

### A crate that already has a configuration

Do not overwrite it. Diff it against the reference and report the
differences, grouped:

- **Lints the project allows that the reference denies** — `unwrap_used` and
  `panic` in particular. Ask why before removing the exception; a crate that
  allows them wholesale usually has a migration story worth writing down.
- **Lints the project denies that the reference does not** — a candidate to
  propose upstream, not to delete.
- **`pedantic` absent** — the most common divergence. Adding it to a mature
  crate produces a large batch of findings; sequence it per the section
  below rather than dropping it in.

Record deliberate differences as comments in the manifest next to the
setting.

### Adopting on an existing crate with a backlog

The failure mode is a first run reporting several hundred warnings, which
gets ignored wholesale and the standard dies on day one. Instead:

1. Land `cargo fmt` first, alone, as one mechanical commit.
2. Enable `clippy::all` and clear it before touching `pedantic`. `all` is
   mostly correctness; `pedantic` is mostly taste, and mixing the two buries
   the findings that matter.
3. Promote `unwrap_used` and `panic` to `deny` last — they are the ones that
   need real code changes rather than mechanical ones.
4. Never adopt by adding a crate-wide `#![allow(...)]`. That records the
   backlog as permanent and removes the pressure that would have cleared it.

## Changing the standard

The reference configuration is the team's, not the crate's. A lint worth
enabling or denying everywhere is changed in
`tech-stacks/rust/skills/rust-code-standards/references/` in the toolkit
checkout, and reaches projects at their next sync. Editing one crate's
`[lints]` to win an argument is how four crates end up with four standards.
