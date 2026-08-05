---
name: generate-code-review
description: Review C code generated from a Simulink/MATLAB model, cross-checking it against the source model rather than just C style. Use after code generation, or when reviewing a generated-code diff.
when_to_use: Use when asked to review generated code, or after running code generation from a model.
---

# Review generated code against its model

Generated C from a model needs a different review than hand-written C: the
model is the source of truth, so the review must confirm the generated
code still matches it.

1. **Confirm regeneration, not hand-editing**: check whether the generated
   files differ from what a clean regeneration would produce. If someone
   hand-edited generated output, that's a finding per the model-based-design
   conventions rule — it must be flagged with a comment and a follow-up
   ticket, not silently kept.
2. **Match subsystem structure**: each generated function/file should trace
   back to a named subsystem in the model. Flag generated code that has no
   obvious model counterpart (often a sign the model and generated output
   are out of sync).
3. **Check the code-generation config**: confirm the checked-in
   configuration (target, optimization level, naming rules) matches what
   was actually used to produce this diff — a mismatched config produces
   code nobody can reproduce.
4. **Apply embedded-C conventions**: run the same checks as the embedded-C
   stack's MISRA baseline rule (and its safety-critical rule if the
   generated code lands under `src/safety/**`) on the generated output
   itself, since it's still C that ships on the target.
5. **Report**: list any hand-edit found, any subsystem/code mismatch, and
   any MISRA/safety finding, each with the file and a concrete next step.
