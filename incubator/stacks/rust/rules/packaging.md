---
paths:
  - "Cargo.toml"
  - "Cargo.lock"
---

# Rust packaging

- Keep `[package]` metadata (`name`, `version`, `edition`, `description`,
  `license`) current; use the latest stable `edition` for new crates.
- Pin direct dependencies with a caret range (`^`, Cargo's default), not an
  exact `=` pin, unless a known incompatibility requires it.
- Use a `[workspace]` at the repo root once a project grows past one crate,
  instead of duplicating dependency versions across separate `Cargo.toml`
  files.
- Commit `Cargo.lock` for binaries/applications; for a library published to
  be depended on by others, `Cargo.lock` may be left out of version control.
- After changing dependencies, run `cargo build` (or `cargo check`) so
  `Cargo.lock` reflects the change — or `cargo add <crate>` when adding a
  new one — and commit the regenerated lock file, don't hand-edit it. Use
  `cargo update -p <crate>` to bump a single dependency; plain `cargo
  update` refreshes every dependency in the lock file and can pull in
  unrelated changes.
- Do not commit the `target/` build directory; add it to `.gitignore`.
