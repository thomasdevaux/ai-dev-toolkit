# Handbook — working with agentic coding

Team reference for **learning to work with an AI coding agent**. Not synced
into any project, not loaded into any session: it's written for people.

## Start here

1. **[practices.md](practices.md)** — the condensed daily practice. Read it
   once, come back to it when a session goes badly.
2. **[token-economy.md](token-economy.md)** — what actually costs, how to read
   the status line, which levers exist.
3. **[plugins-policy.md](plugins-policy.md)** — why we adopt so little, and how
   we decide when we do.
4. **[references.md](references.md)** — where to look things up.

## Setting up your machine

One command, once per machine:

```
toolkit-sync sync --user --toolkit-root <checkout>
```

That installs, under `~/.claude/`: the common block — rules, `caveman`,
`codegraph-setup` — the status line, the drift check, and the 13 official
language servers. All of it applies in *any* folder, which is what makes a
throwaway session worth opening.

After that, opening a session in a scratch folder just works — no `.claude/`
is created, nothing nags you. The toolkit only becomes visible in a real git
repository, where it offers the project baseline and asks which process
profile applies. See [`../README.md`](../README.md) for the project side.
