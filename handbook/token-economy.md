# Token economy

Where the budget actually goes, and which levers exist. The point isn't
frugality for its own sake — it's that a session which reads less and repeats
itself less is also a session that thinks more clearly.

## See it first: the status line

Install it once per machine (`user-statusline`). It shows, on every prompt:
the model, the context window as a filling bar, and rate-limit usage with time
to reset.

Watch the bar rather than the total. What matters is *how fast it fills* on a
given task — that's what tells you a session is reading things it doesn't
need.

## Where the budget goes

Roughly, in order of how often it's the culprit:

1. **Exploration.** Finding where something lives, by opening files. This is
   the big one on an unfamiliar codebase.
2. **Always-loaded context.** `AGENTS.md` and unscoped rules, re-paid every
   session. A 400-line `AGENTS.md` is a permanent tax.
3. **Long sessions.** Everything accumulates; late turns carry all the early
   ones.
4. **Output.** Explanations, summaries, narration between tool calls. Real,
   but usually smaller than people assume.

## The levers, in the order worth pulling

- **Keep `AGENTS.md` under its target.** Costs nothing, applies to every
  session forever. The `context-quality` block enforces it.
- **Point at docs conditionally** instead of loading them. Same idea, applied
  to the doc map.
- **Give the agent a map instead of a search.** `docs/architecture.md` holds
  the module map; the `codegraph` block adds symbol-level navigation so
  "who calls this" stops meaning "open twelve files". This is the lever with
  the largest effect on an unfamiliar repo.
- **Start fresh sessions** at natural boundaries rather than one long one.
- **Compress output** with the `caveman` block when you're in a long
  iteration loop and don't need prose.

## On the numbers

Upstream projects advertise savings: caveman claims ~65% fewer output tokens
on prose and ~8.5% on agentic coding runs; CodeGraph claims ~35% cost and ~70%
tool calls. Those are their measurements, on their benchmarks.

**We haven't measured ours yet.** Until this section says otherwise, treat
those figures as a reason to try a block, not as a result. When we do measure
— same task, same repo, with and without — the numbers go here, including the
ones that disappoint.

The honest prior: the exploration lever (a code map) should dominate, because
exploration is where the budget actually goes. Output compression addresses
the smallest of the four categories above.
