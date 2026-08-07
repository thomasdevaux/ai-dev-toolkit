---
paths:
  - "package.json"
  - "package-lock.json"
---

# Node.js packaging

- Commit the lockfile (`package-lock.json`, `pnpm-lock.yaml`, or
  `yarn.lock`, whichever matches the chosen package manager) for both
  applications and published libraries, so installs are reproducible.
- Pick one package manager per repo (npm, pnpm, or yarn) and stick to it;
  do not let more than one lockfile format accumulate in the same project.
- Set the `engines.node` field to the actual minimum Node version the
  project is tested against, instead of leaving it unset or aspirational.
- After changing dependencies, regenerate the lockfile with the project's
  package manager (`npm install`, `pnpm install`, or `yarn install`) and
  commit the updated file — don't hand-edit it.
- Run `npm audit` (or the equivalent `pnpm audit`/`yarn audit`) before
  release and address any high/critical findings, rather than shipping
  with known vulnerable dependencies.
- Do not commit `node_modules/`; add it to `.gitignore`.
