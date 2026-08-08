# Security policy

## Reporting a vulnerability

Until a public security contact is published, do **not** open a public issue containing a token, Telegram update payload, secret-store path, personal data, or exploit details. Contact the repository owner privately through GitHub.

## Scope priorities

Treat these as security-sensitive:

- manager and child Telegram credentials;
- managed-bot update/token retrieval logic;
- secret-store and filesystem isolation;
- owner authorization;
- duplicate/replay/reconciliation behavior;
- MCP/MRTR request-state integrity;
- profile data handling, especially lead capture.

## Safe disclosure rules for contributors

- Never commit or paste real secrets, raw Bot API updates, private hostnames/paths, IDs, traces, or screenshots containing them.
- Use disposable test bots and redacted fixtures.
- Report suspected exposure immediately; revoke/rotate the exposed credential before further debugging.
- Do not add a fallback token or sample production credential for convenience.

A formal supported-version policy and security contact will be added before the first public release.
