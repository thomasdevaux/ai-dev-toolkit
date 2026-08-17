# References

Where to look things up. Kept short on purpose — a link list nobody prunes is
a link list nobody trusts.

## Claude Code

- **Documentation** — https://docs.claude.com/en/docs/claude-code
  Start here for anything about the harness itself.
- **Settings** (`settings.json`, permissions, environment) —
  https://docs.claude.com/en/docs/claude-code/settings
  This is what `settings_patch` in `sync-manifest.yaml` writes into.
- **Hooks** — https://docs.claude.com/en/docs/claude-code/hooks
  `SessionStart` is the one this toolkit uses, twice over: context check,
  CodeGraph freshness.
- **Skills** — https://docs.claude.com/en/docs/claude-code/skills
  Frontmatter fields, when a skill triggers, `disable-model-invocation`.
- **MCP** — https://docs.claude.com/en/docs/claude-code/mcp
  How an external tool (like CodeGraph) becomes callable.
- **Changelog** —
  https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
  Worth skimming when deciding whether to adopt something: half the reasons to
  wait are in here.

## Agent Skills, generally

- **Official skills repository** — https://github.com/anthropics/skills
  Reference implementations. Also the answer to "does an official one exist
  already?" before writing our own.
- **AGENTS.md convention** — https://agents.md
  Why the context file isn't called `CLAUDE.md` here.

## Third-party content in the baseline

- **caveman** — https://github.com/JuliusBrussee/caveman (MIT). Its skill is
  copied verbatim into `common/skills/caveman/`, with its `LICENSE` and a
  `SOURCE.md` pinning the commit.
- **CodeGraph** — https://github.com/colbymchenry/codegraph (MIT). Not copied:
  it's a binary the `codegraph-setup` skill installs and documents. The
  provenance lives in that skill, where someone about to install it will read
  it.

See [plugins-policy.md](plugins-policy.md) for why copying beats installing,
and where the line falls.

## Ideas borrowed, nothing copied

No file below is in the toolkit — no `SOURCE.md` applies. They're recorded
because knowing where a rule came from is what lets someone argue with it.

- **A Philosophy of Software Design**, John Ousterhout — the source of
  *deep module*, *shallow module*, and the interface-vs-implementation
  complexity comparison that `improve-architecture` is built on.
- **mattpocock/skills** — https://github.com/mattpocock/skills (MIT).
  Its `improve-codebase-architecture` and `codebase-design` skills supplied
  the shape of ours: the fixed vocabulary, the deletion test, the
  one-adapter-is-a-hypothesis rule, the strength badges, and the
  report-then-grill split. Not imported: they depend on skills and a
  `CONTEXT.md` we don't have, and their HTML report pulls Tailwind and
  Mermaid from a CDN, which a corporate proxy turns into an unstyled page.

## This toolkit

- [`../README.md`](../README.md) — adopting it in a project.
- [`../docs/maintaining.md`](../docs/maintaining.md) — how blocks and tiers
  work, and authoring a block.
