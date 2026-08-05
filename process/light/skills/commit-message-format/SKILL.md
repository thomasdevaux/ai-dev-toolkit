---
name: commit-message-format
description: Format a commit message's subject and body when creating a commit. Use whenever actually writing a commit message, as the last step before running `git commit`.
---

# Commit message format

- **Subject**: imperative mood, capitalised, no trailing period, ideally
  under ~70 characters (e.g. "Add retry logic", not "Added retry logic" or
  "Adding retry logic").
- **Body required for non-trivial changes**: if the commit touches more than
  one concern, or the reasoning isn't obvious from the diff, add a blank
  line after the subject and a bulleted body — one bullet per distinct
  change. A single-purpose, self-explanatory change (e.g. a one-line typo
  fix) can ship as a bare subject.
- **Body explains why, not what**: the diff already shows what changed;
  use the body for the reasoning, trade-offs, or context a reviewer can't
  get from the code alone.
- **Not Conventional Commits**: do not prefix subjects with `feat:`,
  `fix:`, etc. — this repo's history doesn't use that format and it is not
  required here.
- Example of a good commit message following this format:

  ```
  Add retry logic to the payment webhook handler

  - Retries transient 5xx responses up to 3 times with backoff, since the
    upstream gateway occasionally times out under load.
  - Logs each retry attempt so failures are traceable without reproducing
    the outage.
  ```

  Compare with an example to avoid — a bare, generic subject with no body
  explaining why the change was made:

  ```
  fix stuff
  ```
