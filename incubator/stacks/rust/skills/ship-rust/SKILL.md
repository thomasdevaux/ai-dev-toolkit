---
name: ship-rust
description: Prepare a Rust project for shipping — formatting, lint, tests, and a release build are mandatory. Use when the user is finishing, releasing, or distributing a Rust crate or tool (not a throwaway script).
when_to_use: Use when asked to "finish", "ship", "release", or "package" a Rust project, or when the project already has a Cargo.toml.
---

# Ship a Rust project

Before considering a Rust project done, all of the following must pass:

1. **Format**: `cargo fmt --check` clean (or run `cargo fmt` and commit the
   result).
2. **Lint**: `cargo clippy -- -D warnings` with zero unresolved issues; fix
   or explicitly justify every reported issue.
3. **Tests**: `cargo test` passes. If there is no test suite yet and the
   crate has meaningful logic (not just argument parsing and I/O), add at
   least one test covering the main code path before shipping.
4. **Packaging**: `Cargo.toml` metadata and dependency pins follow the Rust
   packaging rule.
5. **Release build**: `cargo build --release` succeeds without errors.

Do not report the project as "done" until all five checks pass — state
which ones you ran and their result.
