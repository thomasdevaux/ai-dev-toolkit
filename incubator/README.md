# incubator — parked blocks

This directory holds content written for the toolkit but **not yet
mature**, and deliberately **absent from `sync-manifest.yaml`**: nothing
here can be synced into a project.

## Content

```
stacks/embedded-c/           MISRA, safety-critical, build-toolchain, safety-review
stacks/model-based-design/   Simulink conventions, check-model, generate-code-review
stacks/nodejs/               packaging, web-style, ship-web
stacks/python/               packaging, style, ship-tool, quick-script, quick-fix
stacks/rust/                 packaging, style, ship-rust, quick-fix
demo/                        demo projects that existed only for these blocks
```

`stacks/python/` and `stacks/rust/` still exist at the toolkit root: only
their unvalidated content is parked here, the desktop-architecture skill
that composes them in v1 stays in place.

## Promoting a block

Two conditions, both required:

1. the content has **been used on at least one real project**, and comes
   back corrected rather than untouched;
2. it has been **reviewed by a domain expert** — an embedded developer for
   MISRA rules, not the toolkit's author.

The procedure then: move the block under `stacks/` (or wherever fits),
add its entry to `sync-manifest.yaml` with a `summary:`, and run
`python -m tools.audit --toolkit-root .`. See
[`docs/maintaining.md`](../docs/maintaining.md) for the full procedure.

A parked block that nobody has touched in a year deserves to be deleted
rather than kept: `git log` will bring it back if the need resurfaces.
