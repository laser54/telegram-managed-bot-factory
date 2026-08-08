# Start Here: implementation handoff

This repository intentionally contains documentation before product code. The next agent should not create a generic Telegram/MCP skeleton first. The core Telegram capability must be proven in a disposable end-to-end spike.

## Mission

Build a self-hosted MCP product where a user-owned Telegram manager bot creates user-confirmed managed child bots and a persistent worker provisions an isolated runtime for each child.

**The product is not:** a BotFather wrapper, an arbitrary AI-agent launcher, or a wrapper around a one-child gateway-onboarding flow.

## First task: Telegram capability spike (blocking)

Create a minimal private experiment outside the release implementation. Use a disposable manager bot and disposable child bot. Never place tokens in source, shell history, terminal output, Git, chat, or test fixtures.

Prove and record only safe evidence for all of these:

1. A user-owned manager bot can have Bot Management Mode enabled and `getMe.can_manage_bots == true`.
2. The exact managed-bot creation URL/deep-link shape works against the current Telegram API.
3. The manager receives the actual `managed_bot` update shape after the user confirms creation.
4. `getManagedBotToken` can retrieve the confirmed child credential from the manager context.
5. A duplicate update does not require or justify a second child creation.
6. A child can be launched with its own token and answer an owner-only `/health` request.
7. Whether a bot that was itself managed by another manager can become a manager. This is exploratory, not a prerequisite for the safer default: a separate user-created manager bot.
8. Whether use of the current Hermes gateway bot as a manager creates a competing update-consumer issue. Do **not** solve that by running two pollers on one token; the expected safe design is a separate manager bot.

### Stop conditions

Stop product implementation and update `docs/DECISIONS.md` if Telegram does not support the required manager flow, token retrieval is not available as expected, or the ownership/confirmation semantics contradict this specification. Do not simulate success with invented updates.

## Second task: create the minimal implementation shape

Only after the spike passes:

1. Create `pyproject.toml` for Python 3.11+, using a distribution name `telegram-managed-bot-factory` and a separate import package name chosen after checking naming conventions.
2. Create typed domain models and a SQLite-backed non-secret state machine through TDD.
3. Implement a local file `SecretStore` with enforced `0700` directories and `0600` files.
4. Implement the persistent manager worker with durable polling offset and idempotent update matching.
5. Implement one `owner_echo` isolated child runtime.
6. Implement the stdio MCP control plane: preflight, create request, get request, list instances, start, stop.
7. Add a fake Telegram API integration test before using a live token again.
8. Add the three showcase profiles only after isolation works for `owner_echo`.

## Non-negotiable invariants

- No secret crosses an MCP tool boundary.
- No manager or child token appears in logs, state records, traces, exceptions, source, docs, test fixtures, CI artifacts, or package distributions.
- No external side effect is auto-retried after an ambiguous response.
- A child can access only its own token and instance-local state.
- MCP is correct without connection/session state; `request_id` is explicit and durable.
- A Telegram confirmation is mandatory for each new child; MRTR can improve UX but never replaces it.
- Legacy Hermes must receive a usable stdio fallback even when it cannot negotiate modern MCP extensions.

## Required evidence before calling v0.1 complete

The exact Definition of Done is [ACCEPTANCE.md](ACCEPTANCE.md). The minimum evidence bundle includes:

- live Telegram spike record with secrets redacted;
- unit, fake-API integration, modern-MCP transport, and clean-install test output;
- reproducible `python -m build` and `twine check`;
- safe `hermes mcp test bot-factory` result;
- a 60–90 second demo of one useful child profile;
- package and CI artifact secret scans.

## Recommended reading order

1. This file.
2. [DECISIONS.md](DECISIONS.md), especially the unverified assumptions.
3. [ARCHITECTURE.md](ARCHITECTURE.md).
4. [SPECIFICATION.md](SPECIFICATION.md).
5. [ACCEPTANCE.md](ACCEPTANCE.md).
