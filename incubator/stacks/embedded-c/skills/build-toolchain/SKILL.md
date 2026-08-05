---
name: build-toolchain
description: Build, flash, and test an embedded C project using the project's toolchain. Use when asked to build, flash, or run embedded firmware.
when_to_use: Use when asked to "build the firmware", "flash the board", or "run the embedded tests".
---

# Build toolchain

1. **Locate the build config**: look for `CMakeLists.txt`, a `Makefile`, or
   a vendor-specific project file at the repo root or under `firmware/`.
2. **Build**: run the project's configured build command (e.g. `cmake
   --build build/` or `make`) and treat any compiler warning as a failure,
   per the MISRA baseline rule.
3. **Static analysis**: if a static analyzer is configured (cppcheck,
   clang-tidy, a MISRA checker), run it and resolve or explicitly justify
   every finding before flashing.
4. **Flash**: use the project's documented flashing tool/script (often a
   Python tool following the Python stack's conventions) to load the built
   image onto the target hardware or simulator.
5. **Test**: run the project's hardware-in-the-loop or unit test suite for
   embedded code, and report pass/fail explicitly — do not claim success
   without having run it.
6. If any file touched is under `src/safety/**`, confirm the
   safety-critical rules were applied before reporting the build as ready
   for review.
