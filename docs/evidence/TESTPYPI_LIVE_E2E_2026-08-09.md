# TestPyPI candidate and live managed-child evidence

Date: 2026-08-09

This record intentionally excludes bot usernames, Telegram account IDs, request
IDs, raw updates, credentials, credential-derived values, local filesystem
paths, and private network details.

## Candidate provenance

- GitHub Actions built and published `telegram-managed-bot-factory==0.1.0rc4`
  to TestPyPI using OIDC Trusted Publishing.
- The immutable wheel from TestPyPI was installed into the supported Ubuntu/WSL2
  environment and reported version `0.1.0rc4`.
- Re-running setup reused the complete local enrollment and did not request the
  manager credential again.
- `bot-factory install-hermes` completed without manual YAML editing and Hermes
  0.18 discovered exactly the six default Factory tools.

## Live Telegram result

- The already-enrolled user-owned manager passed `getMe` and management-mode
  preflight with its credential remaining inside the local secret store.
- A new `quick_faq` request returned the Telegram confirmation action through
  the MCP tool contract.
- The owner performed one Telegram creation confirmation. The persistent worker
  matched the managed-bot event, retrieved the child credential once, and moved
  the request to `active`.
- The child ran in its isolated subprocess and displayed three local FAQ items.
- `/faq 1` returned the configured local answer.
- `/health` returned `OK · profile=quick_faq · version=0.1.0rc4`.
- The visible `/start`, `/faq 1`, and `/health` interaction and all replies
  completed within one displayed Telegram minute. No URL was fetched.

An earlier attempt exposed a WSL2 development-host limitation: closing the last
WSL process may stop the distribution and therefore its user services. With the
WSL development environment kept running, `systemd --user`, the manager worker,
and all child subprocesses remained active. This does not change the supported
production target of a continuously running Linux user session.

## Redaction and release gate

The evidence retained in Git is limited to the safe statements above. The local
operator screenshot and terminal output are not release artifacts. Production
PyPI publication and Official MCP Registry publication remain separate gates.
