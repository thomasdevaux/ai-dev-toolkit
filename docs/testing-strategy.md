# Testing strategy

> On hold. Fill this in as soon as there's a deliberate coverage gap worth
> recording. Don't fill it before: invented content here costs more than an
> empty file.

`python -m pytest` covers `tools/sync` and `tools/audit`. The block content
itself (markdown rules and skills) is checked by `python -m tools.audit`, not
by tests.
