# Agent instructions

## First rule

Read `docs/START_HERE.md` before making implementation changes. The Telegram Managed Bots spike is blocking. Do not turn this repository into a generic bot scaffold before proving the actual Telegram flow.

## Product invariants

- User owns the manager bot; Factory owns no hosted manager identity.
- Telegram confirmation is required for every child creation.
- Tokens never enter an LLM prompt, chat, MCP argument/result, CLI argument, YAML, Git, logs, state DB, trace, or fixture.
- Persistent worker owns Telegram update consumption and token retrieval; MCP is only the control plane.
- Child runtime is isolated; only its own secret may reach it.
- Ambiguous external results require reconciliation; no blind retry.
- The default manager bot is separate from the Hermes gateway bot.

## Before editing docs or code

1. Check `docs/DECISIONS.md` for unverified assumptions.
2. Preserve the acceptance tests in `docs/ACCEPTANCE.md`.
3. If an assumption changes, update decision log, specification, and acceptance criteria together.
4. Do not claim a protocol/host feature simply because it appears in the MCP specification; prove capability negotiation and a test.

## Validation minimum

Before calling a change done, run the relevant unit/integration tests once they exist, inspect `git diff`, and scan all changed artifacts for secrets or private infrastructure details.
