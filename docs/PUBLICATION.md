# Publication plan

This document is a release gate, not a claim that publication has happened.

## Artifact sequence

1. Keep the repository private while validating Telegram behavior and security boundaries.
2. Add implementation, tests, CI, and redacted demo evidence.
3. Make the source repository public only after a history/artifact secret scan and documentation review.
4. Build from a clean checkout:
   ```bash
   python -m build
   twine check dist/*
   ```
5. Publish a candidate to TestPyPI using GitHub Actions OIDC Trusted Publishing; create a clean virtual environment and install/test it.
6. Repeat the real Telegram managed-child E2E against the candidate.
7. Tag an approved release and publish to PyPI through a protected GitHub Actions environment.
8. Validate then submit Official MCP Registry metadata pointing at the exact published PyPI version.
9. Consider, but do not promise, a Hermes optional-MCP catalog contribution after independent review.

## Name and identity checklist

- Re-check `telegram-managed-bot-factory` on PyPI immediately before every first upload attempt.
- Ensure the project homepage, repository URL, PyPI package, release version, and README agree.
- Before MCP Registry submission, replace the README marker only if the Registry's current ownership convention requires a different exact form.
- Generate `server.json` only with current schema URL, registry namespace, package identifier, and immutable release version. Do not submit a placeholder.

## GitHub Actions security requirements

- Build and publish are separate jobs.
- Publish consumes only generated distributions from the build job.
- The PyPI publish job has `id-token: write` only at job scope.
- Use a protected `pypi` environment with maintainer approval.
- Do not create/store a long-lived PyPI API token as a GitHub repository secret.
- CI logs and uploaded artifacts must be scanned for token-shaped strings before publication.

## Claims discipline

Do not say “available on PyPI,” “listed in the Official MCP Registry,” “Hermes-compatible,” “secure,” or “one-click” until the related acceptance evidence exists.
