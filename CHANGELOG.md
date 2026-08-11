# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-08-11

### Changed

- Replace Desktop first-run onboarding and the temporary MCP bootstrap catalog with one terminal-only `bot-factory install-hermes` flow for the Linux worker host.
- Make an unconfigured or unhealthy Factory MCP fail closed with a safe terminal-only repair instruction rather than attempting to launch a GUI terminal.
- Retain the verified non-interactive Hermes CLI registration contract so terminal setup remains a single command.

## [0.1.3] - 2026-08-11

### Added

- Add an MCP bootstrap catalog for unconfigured or unhealthy installations that opens secret-bearing setup in a local terminal instead of requesting a Telegram credential through chat.
- Add `bot-factory onboard` for the complete persistent-worker setup path.

### Fixed

- Verify `systemd --user` before any credential prompt and require the worker service to be active before onboarding succeeds.
- Install the exact package version as a durable `uv tool` so systemd never points at an evictable `uvx` cache.
- Keep Desktop-launched setup failures visible and sanitize the environment inherited by the setup terminal.

## [0.1.2] - 2026-08-09

### Fixed

- Correct the PyPI landing-page release status and installation command to point to the published release.

## [0.1.1] - 2026-08-09

### Changed

- Prepared package version `0.1.1` without altering immutable PyPI `0.1.0` metadata.
- Reworked the project landing page around installation, supported use cases, boundaries, and evidence.
- Registered Hermes MCP directly through supported CLI arguments without synthetic stdin confirmation.

### Fixed

- Persist child Telegram update acknowledgements and offsets across restarts.
- Quarantine crash-ambiguous child effects instead of silently duplicating lead notifications, exports, or purge confirmations.

## [0.1.0] - 2026-08-09

### Added

- Durable Telegram Managed Bot request lifecycle with reconciliation and update deduplication.
- Owner-only local secret store and isolated child subprocess credential delivery.
- `owner_echo`, `quick_faq`, `lead_inbox`, and `link_inbox` profiles.
- Six-tool Hermes MCP control plane with modern `2026-07-28` and legacy stdio compatibility.
- Sealed single-use MRTR confirmation state and modern stateless HTTP validation.
- Hidden local setup, owner enrollment, hardened `systemd --user` worker, and Hermes registration.
- Side-effect-free installation that creates no child bots until a separate explicit Factory request and Telegram confirmation.
- Linux/Python 3.11–3.14 acceptance suite, release artifact scans, OIDC Trusted Publishing workflows, provenance attestations, and Registry metadata.

### Security

- Telegram credentials are excluded from MCP, CLI arguments, environment variables, SQLite, manifests, logs, traces, fixtures, and release artifacts.
- Ambiguous external results are never automatically retried.
- Updated `cryptography` to the fixed 50.x release line after the pre-release dependency audit identified advisories in the prior pin.
