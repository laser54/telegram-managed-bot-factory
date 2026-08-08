# Project status

## Current state — v0.1.0 release candidate

- The Telegram Managed Bots live spike passed on 2026-08-08 with redacted evidence.
- Typed package, SQLite state machine, local secret store, persistent worker, isolated runtime, four built-in profiles, six-tool MCP server, setup, systemd unit, and Hermes installer are implemented.
- Windows development suite: 52 passed and one OS-specific symlink test skipped before the final privacy-boundary test was added.
- Ubuntu/WSL2 suite: 53 passed, including POSIX permissions and symlink rejection.
- Hermes 0.18 legacy stdio acceptance discovered exactly six tools.
- Modern MCP acceptance covers discovery, stateless HTTP headers, MRTR expiry/tamper/principal/replay protection, absence of Tasks capability, and trace redaction.
- Wheel and sdist build, `twine check`, dependency audit, package scan, workflow audit, and Git-history credential-shape scan pass locally.
- `server.json` validates with official `mcp-publisher` 1.7.9 and the current Registry schema.

## External gates still open

- Repository remains private until the final public-history review.
- TestPyPI and PyPI Trusted Publisher identities/environments are not configured yet.
- The TestPyPI candidate has not been installed or used for the second live Telegram E2E.
- No `v0.1.0` tag or GitHub Release exists.
- The Official MCP Registry entry is prepared but cannot be published before PyPI.

No README or status statement should claim those external gates have passed until verified.
