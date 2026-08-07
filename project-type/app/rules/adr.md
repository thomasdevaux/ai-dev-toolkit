# Architecture decision records

`docs/adr/` holds one file per decision that constrains the design — the
*why* behind what `docs/architecture.md` describes. **If nobody could
reasonably have decided otherwise, it isn't an ADR**: log routine choices
too and the corpus stops being scannable.

- **Scan `docs/adr/INDEX.md` before any non-trivial work** — a feature, a
  structural change, a new dependency. Only `Accepted` ADRs bind; open the
  ones that do.
- **`Proposed` is an agent's ceiling.** Promoting an ADR to `Accepted` is
  the user's call — never self-accept a decision you just wrote.
- **A file is never moved or deleted**, and a number is never reused —
  inbound links and supersede chains have to stay resolvable.

Writing one is the `write-adr` skill (format, numbering, supersede chains);
gardening the tree is `adr-cleanup`.

## If a request conflicts with an accepted ADR

Stop before acting. Present the conflict, then offer:

1. follow the existing ADR as written;
2. write a new ADR that amends or supersedes it;
3. an explicit, scoped exception the user confirms in the same reply.

Never ship a version that quietly diverges from an `Accepted` ADR and
mention it only afterward.
