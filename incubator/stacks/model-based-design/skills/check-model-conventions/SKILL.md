---
name: check-model-conventions
description: Check a model project's file layout and naming against this project's model-based-design conventions. Use when reviewing a new or changed model file.
when_to_use: Use when asked to check a model's conventions, or before merging a change to a .slx/.mdl file.
---

# Check model conventions

1. **File naming**: confirm model file names are `snake_case` and match
   the component they implement, per the model-based-design conventions
   rule.
2. **Annotations**: confirm every subsystem block has a description
   annotation with a requirement ID. Flag any subsystem missing one.
3. **Naming consistency**: scan signal/parameter names for mixed
   conventions (e.g. both `camelCase` and `snake_case` for the same kind of
   signal) and flag inconsistencies.
4. **Config location**: confirm code-generation configuration is a
   checked-in file next to the model, not only in local MATLAB
   preferences.
5. **Report**: list findings with the model file and the specific
   convention violated. If everything checks out, say so explicitly.
