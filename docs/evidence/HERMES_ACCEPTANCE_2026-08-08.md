# Redacted Hermes compatibility evidence — 2026-08-08

Environment: local Hermes 0.18.0 using its bundled legacy MCP client and stdio transport. The Factory used isolated temporary XDG and Hermes directories with a synthetic non-production secret.

Safe observed results:

- `hermes mcp add` connected successfully;
- exactly six Factory tools were discovered and enabled;
- `hermes mcp test` connected through stdio and rediscovered the same six tools;
- the automated legacy client test invoked `factory_preflight` and received structured content without credential, owner identity, or filesystem data;
- no production Telegram account, token, identifier, username, local path, or raw protocol payload is retained in this evidence.

This proves legacy stdio compatibility for the tested Hermes version. It does not claim support for Hermes modern MCP extensions or inclusion in a Hermes curated catalog.
