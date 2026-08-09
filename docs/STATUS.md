# Project status

## Current state — v0.1.0 release candidate

- The Telegram Managed Bots live spike passed on 2026-08-08 with redacted evidence.
- Typed package, SQLite state machine, local secret store, persistent worker, isolated runtime, four built-in profiles, six-tool MCP server, setup, systemd unit, and Hermes installer are implemented.
- Windows development suite: 54 passed and one OS-specific symlink test skipped.
- Ubuntu/WSL2 suite: 55 passed, including POSIX permissions and symlink rejection.
- Hermes 0.18 legacy stdio acceptance discovered exactly six tools.
- Modern MCP acceptance covers discovery, stateless HTTP headers, MRTR expiry/tamper/principal/replay protection, absence of Tasks capability, and trace redaction.
- Wheel and sdist build, `twine check`, dependency audit, package scan, workflow audit, and Git-history credential-shape scan pass locally.
- `server.json` validates with official `mcp-publisher` 1.7.9 and the current Registry schema.
- The GitHub repository is public and the TestPyPI/PyPI Trusted Publisher identities and protected environments are configured.
- TestPyPI candidate `0.1.0rc4` was installed in Ubuntu/WSL2 and passed the second live managed-child E2E, including a visible `quick_faq` answer and safe `/health` result. See the [redacted evidence](evidence/TESTPYPI_LIVE_E2E_2026-08-09.md).

## External gates still open

- No `v0.1.0` tag or GitHub Release exists.
- Production PyPI publication still requires protected-environment approval.
- The Official MCP Registry entry is validated but cannot be published before PyPI.

No README or status statement should claim those external gates have passed until verified.
