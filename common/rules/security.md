# Security

- Never commit secrets: API keys, tokens, passwords, private certificates, or
  customer data. If you are unsure whether a value is sensitive, treat it as
  sensitive.
- Every repository must have a `.gitignore` that excludes `.env`, `.env.*`,
  `*.pem`, `*.key`, `credentials.json`, and any local settings file that can
  hold secrets.
- Load secrets from environment variables or a secrets manager, never from a
  file checked into version control.
- If a secret is accidentally committed, do not just delete it in a follow-up
  commit — the old value stays in git history. In order: rotate the
  credential at the provider so the leaked value stops working, then remove
  it from history (`git filter-repo` or the provider's equivalent, which
  needs a force-push and a re-clone by everyone holding a copy), then report
  it through the project's incident channel.
- Do not disable or bypass security tooling (dependency scanners, secret
  scanners, pre-commit hooks) to unblock a commit. Fix the underlying issue
  or get an explicit, documented exception.
- Review third-party dependencies before adding them: prefer actively
  maintained packages, and check for known vulnerabilities (e.g.
  `pip-audit`, `npm audit`) before merging a new dependency.
