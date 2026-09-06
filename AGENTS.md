# Agent instructions

## First rule

Read `docs/START_HERE.md` and its referenced evidence before making implementation changes. Do not re-run a completed Telegram Managed Bots spike solely because this instruction exists. Block only work that depends on an unproven capability or invalidated evidence. Preserve the proven separate-manager flow and all product invariants; do not turn this repository into a generic bot scaffold.

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

Before calling a change done, run the relevant unit/integration tests once they exist, inspect `git diff`, and scan all changed artifacts for secrets or private infrastructure details. Validation does not authorize publication: commit only when included in the requested scope, and obtain explicit user authorization before push, opening a PR, merge, release, submission, or deployment. Before any push/merge that triggers deployment, satisfy the applicable deployment and PROD confirmation gates.
