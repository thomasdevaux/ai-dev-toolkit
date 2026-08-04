# Decisions log

## D-01 — Track requirements in a single flat file

Status: settled

Decision: keep all requirements for this demo project in one
`docs/requirements.md` file rather than one file per requirement.

Why: this is a small fixture; a flat list is cheaper to scan than opening
multiple files, matching `process/light`'s
`rules/requirements.md`.
