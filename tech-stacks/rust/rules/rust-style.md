---
paths:
  - "**/*.rs"
---

# Rust code standards

The mechanical part is enforced by tooling, not by this file: `cargo fmt`
for formatting, `cargo clippy` for lint. Their configuration is the actual
standard — `rust-code-standards` holds the ready-to-copy version and the
procedure for adopting it. If a crate has no `[lints]` table yet, say so
once and offer to run that skill.

What tooling cannot decide, and this file does:

- **Run the tools once per task, not per edit.** While working: `cargo fmt` and
  the targeted `cargo test <module>` of what changed, which also compiles it.
  When the task's code is finished, and unless a project gate runs them
  (`verification-tiers`): `cargo clippy --all-targets -- -D warnings`, then
  `cargo test`. That clippy command is the same whenever it runs: dropping
  `--all-targets` or `-D warnings` to go faster is not allowed. A finding is
  either fixed or allowed with a reason — never left reported.
- **Silencing needs a named lint and a why.** `#[allow(clippy::too_many_arguments)]`
  alone is not acceptable; the same line with a comment saying what makes it
  the right call is. Crate-wide `#![allow(...)]` for anything other than a
  deliberate, documented team decision is not acceptable. One such decision:
  `#![allow(clippy::needless_pass_by_value)]` on a Tauri `commands/` module,
  whose signatures `#[tauri::command]` imposes.
- **Errors propagate as `Result`, not panics.** `?` is the default.
  `.unwrap()` and `.expect()` belong in tests, in `main` where the failure is
  genuinely terminal, and where an invariant makes the failure impossible —
  in which case `.expect("why it cannot fail")` states that invariant.
- **Give errors a type.** A library crate defines its own error enum
  (`thiserror` is the usual way); `anyhow` belongs in binaries, where the
  caller is a human and the context string is the point. A crate returning
  `Box<dyn Error>` from its public API has made every caller's error
  handling untyped.
- **Default to the narrowest visibility that works.** Private, then
  `pub(crate)`, and `pub` only for what is genuinely the crate's API. Widening
  later is free; narrowing later is a breaking change.
- **Borrow before cloning.** A `.clone()` to escape the borrow checker is a
  design signal, not a fix — if it stays, the comment says why the ownership
  actually belongs there.
- **`unsafe` needs a `// SAFETY:` comment** stating the invariant the caller
  must uphold. No exceptions; this is what `clippy::undocumented_unsafe_blocks`
  checks and why it is enabled.

Adding a lint to the shared configuration is a team decision, not a
per-crate one: propose it against the toolkit's `rust-code-standards`
reference rather than editing one crate's `[lints]` alone.
