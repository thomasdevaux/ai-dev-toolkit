---
paths:
  - "model/**"
  - "**/*.slx"
  - "**/*.mdl"
---

# Model-based design conventions

- Model file names use `snake_case` and match the subsystem/component they
  implement (e.g. `brake_controller.slx`, not `Model1.slx`).
- Every subsystem block has a description annotation stating its purpose
  and the requirement ID it implements, mirroring the traceability
  convention used in the embedded-C stack's `safety-critical.md`.
- Signal and parameter names use the project's naming convention
  consistently across the model (no mixing `camelCase` and `snake_case` for
  signals of the same kind).
- Code generation configuration (target hardware, optimization level,
  naming rules) lives in a checked-in config file next to the model, not
  only in the engineer's local MATLAB preferences.
- Regenerate code from the model rather than hand-editing generated C —
  hand-edits are lost on the next generation and hide the actual source of
  truth.
- Any manual patch to generated code (rare, and only when regeneration
  isn't immediately possible) must be flagged with a comment explaining why
  and a follow-up ticket to fix it at the model level.
