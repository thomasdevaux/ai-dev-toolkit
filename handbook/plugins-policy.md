# What we adopt, and how

We adopt little, deliberately. Not conservatism — the tooling underneath moves
fast enough that most third-party additions are solving a problem that will be
native in two releases, and every one of them is something the team has to
understand, maintain and eventually remove.

## The rule of thumb

**If it overlaps a native feature, don't adopt it.** Bet on the native path
improving. The cost of waiting is some friction; the cost of adopting is a
dependency that quietly diverges from the platform.

### The Superpowers example

Superpowers was a genuinely useful plugin a few months ago: it added planning
discipline, spec files, structured workflows — things the harness didn't do
well. Then plan mode, skills and subagents landed natively and did most of it.
What remained was a parallel way of working, competing with the built-in one.

We dropped it. The plan and spec files it produced are archived under
`docs/history/superpowers/` — kept as a record, not as a practice.

The lesson isn't "Superpowers was bad". It's that **adopting the right tool at
the right moment still leaves you holding it after the moment passes**, and
nobody enjoys being the one to say so.

## The four options

| Option | When | Cost |
| --- | --- | --- |
| **Wait for native** | The gap is real but obviously on the platform's path | Friction now |
| **Depend on a plugin** | Officially maintained, no overlap, you want its updates | Black box; updates you didn't choose |
| **Vendor it** | Good content, you want to read/adapt/pin it | You own updates forever |
| **Write our own** | The need is specific to how this team works | You own all of it |

## Why we copy rather than install

The baseline ships `caveman` (MIT) as plain text: `common/skills/caveman/`
holds the skill exactly as upstream wrote it, its `LICENSE`, and a `SOURCE.md`
pinning the commit it came from.

We took the same approach with the official `claude-md-management` plugin, and
then went one step further: having read its criteria, we folded the useful
parts into our own `audit-project-context` skill — retargeted to `AGENTS.md`,
which is what we actually use — and dropped the copy. That's the normal end
state for borrowed *criteria*, as opposed to borrowed *text*: you keep the
idea, credit the source, and stop carrying the file.

Copying buys three things a plugin install doesn't:

- **You can read it.** The whole point of this toolkit is that mechanisms are
  visible, not hidden behind an install command. Someone learning to work with
  an agent should be able to open the file and see what it tells the agent.
- **You can adapt it.** `claude-md-management` speaks about `CLAUDE.md`; we
  work `AGENTS.md`-first. Copied, that's an edit. As a dependency, it would be
  a permanent contradiction between the plugin and our own rule.
- **Nothing changes under you.** An upstream update is a diff someone reads,
  on our schedule.

**And a binary is a different case.** CodeGraph isn't copied — there's nothing
to copy, it's an executable. What we own there is the part that decides
whether it gets used and how it's removed: a rule, a setup skill carrying its
provenance and pinned version, and a freshness check. Same principle, applied
to what can actually be held.

What it costs: **no automatic updates**. Nobody will tell you the upstream
improved. That's a real loss, accepted knowingly — write it in `SOURCE.md` so
the next person knows there's an upstream at all.

## Before adopting anything, ask

1. Does the platform already do this, or obviously will?
2. Who maintains it, and what happens when they stop?
3. Can we read what it actually does — or is it an install command and trust?
4. What does removing it look like? (If nobody can answer, don't adopt it.)
5. Is the value measured, or advertised?

Question 4 is the one that gets skipped, and it's the one that hurts.
