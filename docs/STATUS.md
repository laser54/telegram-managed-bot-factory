# Project status

## Current state

- **Repository:** private design/planning repository.
- **Code:** not started; the blocking Telegram capability spike has passed.
- **Distribution:** not published; no package is installed from PyPI.
- **Official MCP Registry:** not submitted.
- **Telegram live E2E:** core managed-bot flow verified with disposable bots on 2026-08-08; safe evidence is in `docs/evidence/TELEGRAM_SPIKE_2026-08-08.md`.
- **Hermes integration:** not yet run against this product.

## Name check performed during bootstrap

`telegram-managed-bot-factory` returned HTTP 404 from the PyPI JSON endpoint during initial setup, and the GitHub repository name was available under `laser54`.

This check is evidence of availability at that moment only. PyPI package names are not reserved by a 404 check. Re-check immediately before TestPyPI/PyPI upload.

## Next milestone

Create the minimal implementation shape described in [START_HERE.md](START_HERE.md), beginning with typed domain models and the non-secret state machine.

## Before making the repository public

1. Remove all private-environment references and confirm no real usernames, paths, topology, IDs, fixtures, or credentials remain.
2. Run a full Git history and artifact secret scan.
3. Add working code, tests, CI, security policy, release documentation, and live E2E evidence.
4. Ensure every README claim is substantiated.
5. Decide public issue/discussion settings and license with the maintainer.
