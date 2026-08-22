# Project status

## Current state — v0.1.0 released

Unreleased `0.1.1` is being prepared in the repository. It does not modify the
already-published, immutable PyPI `0.1.0` metadata.

- The Telegram Managed Bots live spike passed on 2026-08-08 with redacted evidence.
- Typed package, SQLite state machine, local secret store, persistent worker, isolated runtime, four built-in profiles, nine-tool MCP server, setup, systemd unit, and Hermes installer are implemented.
- Windows development suite: 54 passed and one OS-specific symlink test skipped.
- Ubuntu/WSL2 suite: 55 passed, including POSIX permissions and symlink rejection.
- Hermes 0.18 legacy stdio acceptance discovered exactly six tools.
- Modern MCP acceptance covers discovery, stateless HTTP headers, MRTR expiry/tamper/principal/replay protection, absence of Tasks capability, and trace redaction.
- Wheel and sdist build, `twine check`, dependency audit, package scan, workflow audit, and Git-history credential-shape scan pass locally.
- `server.json` validates with official `mcp-publisher` 1.7.9 and the current Registry schema.
- The GitHub repository is public and the TestPyPI/PyPI Trusted Publisher identities and protected environments are configured.
- TestPyPI candidate `0.1.0rc4` was installed in Ubuntu/WSL2 and passed the second live managed-child E2E, including a visible `quick_faq` answer and safe `/health` result. See the [redacted evidence](evidence/TESTPYPI_LIVE_E2E_2026-08-09.md).
- Signed tag `v0.1.0`, the GitHub Release, and its wheel/sdist artifacts are public.
- Production PyPI `0.1.0` was published with OIDC Trusted Publishing and digital attestations.
- A clean production `uvx` resolved `0.1.0`; the installed Hermes server discovered exactly six tools and returned a ready, healthy preflight with no pending or reconciliation work.
- Official MCP Registry API returns `io.github.laser54/bot-factory` version `0.1.0`, backed by `telegram-managed-bot-factory==0.1.0` over stdio.

## Release notes

- All v0.1.0 publication gates are complete. See the [publication evidence](evidence/RELEASE_0.1.0_2026-08-09.md).
- The immutable PyPI `0.1.0` long description was built while external gates were still pending and therefore retains release-candidate status wording. Repository documentation records the completed public-alpha release; unreleased `0.1.1` carries the corrected wording.
- The Official MCP Registry is still a preview service and its listing is not a security certification.

No Hermes curated-catalog listing is claimed.
