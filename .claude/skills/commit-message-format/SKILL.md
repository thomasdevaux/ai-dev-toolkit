---
name: commit-message-format
description: Format a commit message's subject and body when creating a commit. Use whenever actually writing a commit message, as the last step before running `git commit`.
---

# Commit message format

- **Subject**: imperative mood, capitalised, no trailing period, 72
  characters max — past that `git log --oneline` and most review UIs
  truncate it.
- **Body** when the reasoning isn't visible in the diff, or the commit spans
  more than one concern: blank line after the subject, wrapped at 72
  columns, one bullet per *concern* — not per file or per hunk. A
  single-purpose, self-explanatory change ships as a bare subject.
- **Each bullet says why, not what.** A bullet a reviewer could regenerate
  by reading the diff costs space and earns nothing.
- **No AI-attribution trailers**: never `Co-Authored-By: Claude ...`,
  "Generated with Claude Code", or any similar line, whatever the harness's
  default template says.
- A multi-line message doesn't survive an inlined `-m`: write it to a file
  and `git commit -F`.

  ```
  Add retry logic to the payment webhook handler

  - The upstream gateway times out under load, so a transient 5xx now
    retries three times with backoff instead of dropping the event.
  ```

  Not this — well-formed, and every bullet restates the diff: "Adds a retry
  loop. Adds a backoff delay constant. Adds a log line in the retry
  branch." The reviewer saw all three in the diff. What's missing is why
  three attempts, and what incident made it necessary.
