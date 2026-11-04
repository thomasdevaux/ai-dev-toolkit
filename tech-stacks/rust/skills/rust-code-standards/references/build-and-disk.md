# Build configuration and disk

What the build-side references are for, and how to keep `target/` from filling
the disk. The files themselves are the standard; this explains them.

## The files

| Reference | Goes to | What it settles |
|---|---|---|
| `rust-toolchain.toml` | project root | one pinned compiler, with `clippy` and `rustfmt` |
| `cargo-config.toml` | `.cargo/config.toml` | the `rust-lld.exe` linker on Windows MSVC |
| `Cargo-profiles.toml` | root `Cargo.toml` | dev and release profiles |
| `clean.ps1`, `clean.test.ps1` | `scripts/` | the `target/` cap |

Also in the root `Cargo.toml`: `edition = "2024"` and `resolver = "3"`.

**`rust-version`**: an application does not need it — `rust-toolchain.toml`
already pins the compiler. A library published for others sets it. If a
project does set it, it moves in the same commit as `rust-toolchain.toml`:
with resolver 3 it steers which dependency versions are picked, so a stale
value silently selects older crates.

## Versioned or machine-local

Shared settings — what colleagues and CI need — are versioned in the project.
`%USERPROFILE%\.cargo\config.toml` is for what belongs to one machine only:

- `[http] check-revoke = false` behind a proxy that blocks revocation checks
  (see `corporate-proxy.md`);
- `[build] rustc-wrapper = "sccache"` if sccache is installed: it shares
  compiled dependencies between projects, but a versioned wrapper breaks
  every machine without it. Its cache (`%LOCALAPPDATA%\Mozilla\sccache\cache`,
  10 GiB by default) counts toward the disk;
- a shared `target-dir` or `build-dir`, as an opt-in only. It saves disk
  across projects but mixes their artefacts, so `clean.ps1` and `cargo sweep`
  can no longer reason per project, and a deep shared path reaches the
  Windows 260-character limit sooner when long paths are disabled.

## Keeping target/ in check

- **`scripts/clean.ps1`** runs at the start of the dev and build scripts. It
  prints the size of the build dirs, prunes stale incremental sessions, and
  removes the build dirs past **30 GB**. `RUST_TARGET_MAX_GB` (a user
  environment variable, one value for every project; `0` = no cap) or
  `-MaxGB N` changes the cap; `-Force` cleans now. `clean.test.ps1` is its
  test, run on a fake target dir.
- **Every couple of weeks**: `cargo sweep --time 14` removes what no build has
  touched for 14 days (`cargo install cargo-sweep` once).
- **After every `rustup update`**: `cargo sweep --installed` removes the
  artefacts of toolchains no longer installed — never reused, and often the
  bulk of an old `target/`.

Without a cap, `target/` grows by tens of GB and fills a laptop disk. With the
profiles above, a fresh debug build is 3-10 GB.

## When the disk is full

In this order, stopping as soon as there is room:

1. `scripts/clean.ps1 -Force` in each project.
2. `cargo sweep --installed`, then `cargo sweep --time 14`, in each project.
3. Forgotten `target/` dirs: one left behind by an old layout
   (`src-tauri/target` from before a workspace move), a project no longer
   built. Deleting one only costs a rebuild.
4. The sccache cache, if enabled; `npm cache clean --force`.
5. `%USERPROFILE%\.cargo\registry\cache` and `\src`: Cargo downloads again
   what it needs.
