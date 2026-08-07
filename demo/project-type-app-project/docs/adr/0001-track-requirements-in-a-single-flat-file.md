# 0001. Track requirements in a single flat file

Status: Accepted
Date: 2026-01-15

## Context

This is a small fixture. Requirements could live one-per-file or in a single
list.

## Decision

Keep all requirements for this demo project in one `docs/requirements.md`
file rather than one file per requirement.

## Consequences

A flat list is cheaper to scan than opening multiple files, matching
`project-type/app`'s `rules/requirements.md`.
