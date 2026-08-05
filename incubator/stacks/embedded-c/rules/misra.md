---
paths:
  - "**/*.c"
  - "**/*.h"
---

# MISRA-style baseline rules

Applies to all embedded C in this project, not just safety-critical paths
(see `safety-critical.md` for the stricter subset under `src/safety/**`).

- No dynamic memory allocation (`malloc`/`free`) after system
  initialization completes.
- No recursion — use iteration or an explicit stack/queue instead.
- Use explicit-width integer types (`uint8_t`, `int32_t`, ...) from
  `<stdint.h>` instead of `int`, `long`, or `short` for anything with a
  defined range or hardware register width.
- Every `switch` has a `default` case, even if it only asserts unreachable.
- No implicit fallthrough between `switch` cases; mark intentional
  fallthrough with a comment.
- Every function has a single point of return where practical; early
  returns for guard clauses are fine, but avoid deeply nested conditional
  return paths.
- All warnings from the configured compiler flags are treated as errors —
  no `-Wno-*` added to silence a warning without a documented reason.
