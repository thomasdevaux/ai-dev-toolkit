# Testing strategy

- Any non-trivial new feature or bugfix needs at least one automated test
  covering its main path before it's considered done — independent of tech,
  and consistent with the per-tech shipping gates (e.g. `ship-tool`,
  `ship-web`) that already check this at release time.
- No numeric coverage threshold is imposed — too rigid for small tools and
  utilities.
- Keep `docs/testing-strategy.md` current: what's covered by automated
  tests, what's deliberately left uncovered (and why), and how to run the
  suite.
- If you add coverage the doc doesn't mention, or a gap the doc doesn't
  disclose, update the doc in the same change.
