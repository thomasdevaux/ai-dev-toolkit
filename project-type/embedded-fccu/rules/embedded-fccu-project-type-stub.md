# Embedded / FCCU project type (not yet designed)

This profile marks embedded, safety-critical or certified software. Its own
discipline isn't designed yet, so:

- Apply `project-type/app`'s rules from the toolkit checkout by hand — none
  of its files land here, the two profiles being mutually exclusive.
- When the project's needs exceed them (certification traceability, formal
  audit trail, real-time constraints), say so to the user instead of
  inventing ad hoc process.
