---
paths:
  - "**/*.rs"
---

# Rust style

- Format with `cargo fmt` and lint with `cargo clippy -- -D warnings` before
  committing; fix or explicitly justify every reported issue.
- Prefer `Result`/`Option` and the `?` operator for error propagation over
  panicking; reserve `.unwrap()`/`.expect()` for tests or cases already
  proven infallible.
- Default items to `pub(crate)` (or private); only widen visibility to `pub`
  when the item is part of the crate's public API.
- Prefer borrowing (`&T`/`&mut T`) over cloning unless ownership is actually
  needed.
- Keep functions under ~50 lines; extract a helper when a function does more
  than one thing.
- Run `cargo test` before committing; it is this stack's enforcement point
  for the org-wide testing strategy (`testing-strategy.md`).
