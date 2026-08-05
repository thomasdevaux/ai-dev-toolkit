# Architecture decision records

`docs/adr/` holds one file per decision that constrains the design — the
*why*; `docs/architecture.md` stays the *what*. One file per ADR, not a flat
log: each decision gets its own supersede chain and archive trail.

## Layout

- `docs/adr/active/<NNNN>-<slug>.md` — decisions currently in force.
- `docs/adr/archive/<NNNN>-<slug>.md` — deprecated or superseded decisions,
  moved here physically, never deleted.
- `docs/adr/INDEX.md` — one line per ADR, active and archived: id, title,
  status, one-sentence summary, tags. Scan this first; open a full ADR only
  when the task actually needs its reasoning.

Numbers are sequential across active and archive combined, assigned once,
never reused — an archived ADR keeps its number.

## Format (Nygard)

```markdown
# <NNNN>. <Title>

Status: <Proposed | Accepted | Deprecated | Superseded by ADR-<NNNN>>

## Context

<the forces at play, stated as neutrally as the decision allows>

## Decision

<the decision, stated plainly>

## Consequences

<what this makes easier, harder, or forecloses>
```

## Lifecycle

- **Never edit an entry to reverse it.** Add a new ADR, mark the old one
  `Superseded by ADR-<NNNN>`, and move its file from `active/` to `archive/`.
- **Deprecating** a decision with nothing replacing it: same move, status
  `Deprecated`, say why in its own `Consequences` section.
- `docs/adr/INDEX.md` is kept in sync with the files on disk — by hand, or
  with the `adr-cleanup` skill.
- Log the ADR in the same change that makes the decision, not as an
  afterthought.

## If a request conflicts with an active ADR

Stop before acting. Present the conflict, then offer:

1. follow the existing ADR as written;
2. write a new ADR that amends or supersedes it;
3. an explicit, scoped exception the user confirms in the same reply.

Never ship a version that quietly diverges from an `Accepted` ADR and
mention it only afterward.
