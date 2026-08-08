# Contributing

This project is preparing the v0.1.0 public release. Read [docs/START_HERE.md](docs/START_HERE.md) before editing code or expanding scope.

## Development rules

1. Start from the live Telegram capability spike; do not replace missing evidence with mocks.
2. Use TDD for state transitions, token boundaries, path isolation, authorization, and idempotency.
3. Keep changes small and reviewable. Every new side effect needs a failure/reconciliation case.
4. Never commit credentials, raw updates, private infrastructure details, or generated secret files.
5. Do not add a feature from a new MCP specification without client capability negotiation and a working test.
6. Update `docs/DECISIONS.md`, `docs/SPECIFICATION.md`, and `docs/ACCEPTANCE.md` when a central assumption changes.

## Pull request readiness

Before requesting review, run `uv run ruff check .`, `uv run mypy src`, and `uv run pytest -q`; provide relevant output and state whether a change touches security boundaries, external Telegram effects, or package/public documentation.

## Scope discipline

The v0.1 product is a safe factory for a few built-in profiles. It is not a general arbitrary-code generator or generic agent-hosting platform.
