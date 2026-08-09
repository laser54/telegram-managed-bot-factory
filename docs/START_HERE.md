# Start Here: maintainer handoff

The blocking Telegram spike, implementation, and v0.1.0 publication are complete. Preserve the proven flow and consult [STATUS.md](STATUS.md), [PUBLICATION.md](PUBLICATION.md), and the [release evidence](evidence/RELEASE_0.1.0_2026-08-09.md) before planning follow-up work.

## Mission

Build a self-hosted MCP product where a user-owned Telegram manager bot creates user-confirmed managed child bots and a persistent worker provisions an isolated runtime for each child.

**The product is not:** a BotFather wrapper, an arbitrary AI-agent launcher, or a wrapper around a one-child gateway-onboarding flow.

## First task: Telegram capability spike (blocking)

**Completed 2026-08-08 for the safe baseline.** See the redacted evidence in
[`evidence/TELEGRAM_SPIKE_2026-08-08.md`](evidence/TELEGRAM_SPIKE_2026-08-08.md).
The managed-child-as-manager question remains exploratory and does not block the
separate-manager implementation.

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

## Implemented v0.1 shape

Completed after the spike passed:

1. Python 3.11–3.14 package and locked dependencies.
2. Typed SQLite-backed non-secret state machine.
3. Local `SecretStore` with verified `0700` directories and `0600` files.
4. Persistent manager worker with durable offset and idempotent update matching.
5. Isolated child runtime and four bounded built-in profiles.
6. Six-tool dual-era MCP control plane.
7. Fake Telegram integration and modern/legacy protocol acceptance tests.
8. Linux setup, hardened user service, Hermes registration, and trusted release workflows.

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
