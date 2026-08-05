# Daily practice

The condensed version. Everything here is something that goes wrong often
enough to be worth stating.

## Frame before you code

The single highest-leverage habit. A vague instruction produces plausible work
in the wrong direction, and you pay to read it before you find out.

- Say what "done" looks like. If you can't, that's the first thing to work out
  — with the agent, out loud.
- Name the constraints it can't infer: what must not change, what's already
  been tried, what the deadline actually is.
- For anything structural, use **plan mode** first. Reviewing a plan costs
  minutes; reviewing a wrong implementation costs an afternoon and you'll be
  tempted to keep it because it exists.

## Context is a budget, not a bucket

Everything loaded is paid for on every turn, and the more there is, the less
each piece weighs.

- `AGENTS.md` loads every session. It's the most expensive text in the repo —
  it earns its 150 lines or it gets cut.
- Point at documents with a condition ("open this if you're changing X")
  rather than loading them for good measure.
- A long session drifts. When you notice yourself re-explaining, start a fresh
  session rather than pushing through — the restart is cheaper than the drift.

## Read the diff, not the summary

The agent's account of what it did is a summary written by the same process
that did it. It's usually accurate, and reviewing it is not reviewing the code.

- Read the diff. Every time. It's the only artifact that can't be persuasive.
- Ask for the tests to be run and the **output** shown, not "tests pass".
- Treat "should work" as "hasn't been run".

## Push back

An agent that agrees with everything is a defect, not a courtesy. If it folds
the moment you disagree, you've lost the only second opinion you had — ask it
to defend or refute the point on the merits.

Conversely, when it pushes back on you, that's the moment worth reading
carefully. It's what a colleague would do.

## Split work deliberately, not reflexively

Sub-agents and parallel work sound efficient and often aren't: each one starts
cold and re-derives what your session already knows.

Split when the pieces are genuinely independent and each is self-contained.
Don't split to feel fast.

## Know when to stop

- Three failed attempts at the same problem means the framing is wrong, not
  that the fourth will land. Step back and re-frame.
- When something is finished and verified, say so and stop. Endless polish is
  how a working change becomes a risky one.
- When you're not sure it's right, don't merge it. "The agent wrote it" has
  never been a review.
