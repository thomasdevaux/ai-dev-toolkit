# Decisions log

- Keep a dedicated `docs/decisions.md` — decisions that constrain the design are
  never buried inside `docs/architecture.md`; that file stays the *what*, this
  one is the *why*.
- One file, not one file per decision — at this scale a flat file is cheaper to
  scan than opening N files, and git history per decision isn't worth the cost.
- Each entry: a `D-<NN>` id, a short title, a status (**settled**, **provisional**,
  or **superseded**), the decision stated plainly, a **Why** line explaining the
  reasoning. Add a **Rejected** line when a real alternative was considered and
  lost, and a **Cost accepted** line when the decision gives something up worth
  naming. Skip either when there's nothing genuine to say.
- Alternatives listed as rejected were examined — don't repropose one without an
  argument that wasn't available when it was rejected.
- Never edit a past entry to reverse it. Append a new entry marked
  **superseded**, and say what replaced it.
- Log a decision in the same change that makes it, not as an afterthought.
