# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes, after public release |
| Unreleased development snapshots | Best effort only |

## Reporting a vulnerability

Use GitHub private vulnerability reporting from the repository Security tab when available. Otherwise contact the repository owner privately through GitHub. Do not open a public issue containing a credential, raw Telegram update, personal data, local path, trace, or exploit detail.

If a credential may have been exposed, revoke or rotate it in Telegram before further debugging. Do not send the value to the maintainer as proof.

## Security-sensitive scope

- manager and child Telegram credentials;
- managed-bot update matching and token retrieval;
- filesystem permissions, symlink/traversal defense, and subprocess isolation;
- owner authorization and profile data handling;
- duplicate, replay, reconciliation, and MRTR request-state behavior;
- MCP result, error, log, and trace redaction;
- captured-PTY and non-interactive prompt injection during first-run onboarding.

Manager credentials are accepted only by the local hidden prompt in an interactive
terminal. Setup fails closed for piped stdin. Do not relay that prompt or its answer
through an agent, chat, MCP argument, command line, environment variable, log, or trace.

## Disclosure rules

- Reproduce with disposable bots and synthetic runtime-generated sentinels.
- Share only the minimum redacted evidence required to locate the issue.
- Never add a fallback credential, production payload, or private infrastructure reference to a fixture.
- Maintainers will acknowledge a complete private report as soon as practical and coordinate remediation and disclosure based on impact.
