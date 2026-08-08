# Decisions, evidence, and open questions

## Decided

| Decision | Rationale |
|---|---|
| Distribution/repository name: `telegram-managed-bot-factory` | Descriptive, distinct from generic bot generators, and PyPI returned 404 during repository bootstrap. It is not reserved until upload. |
| MCP server name: `bot-factory` | Short and task-focused; it is independent of the Python distribution name. |
| Separate user-owned manager bot | Avoids conflating Hermes gateway updates with factory updates; makes ownership and runtime boundaries clear. |
| Persistent worker separate from MCP | MCP/Hermes may be transient; Telegram confirmation updates and child lifecycle are durable work. |
| Child token acquired only by worker after Telegram confirmation | Keeps secrets out of LLM/MCP context and removes manual copy-paste. |
| Local stdio first | Best secret boundary and simplest Hermes integration. Remote HTTP is a tested capability, not the first deployment requirement. |
| Modern MCP with compatibility fallback | Use stable 2026-07-28 core features where applicable and retain the durable `request_id` status flow across all hosts. Do not advertise the experimental Tasks extension until an official Python implementation and host support are proven. |
| No general AI child profile in v0.1 | Model secrets, costs, tools, and content policy need a separate security design. |
| MIT planned | Maximizes public reuse; validate final licensing and dependency compatibility before release. |

## Must be proven, not assumed

| Assumption | Required evidence | Status |
|---|---|---|
| Managed-bot manager setup works for a user-owned bot | live `getMe.can_manage_bots` | verified 2026-08-08; see `docs/evidence/TELEGRAM_SPIKE_2026-08-08.md` |
| Deep-link, update, and token retrieval match design | redacted disposable E2E | verified 2026-08-08; update fields were `bot` and `user` |
| A managed child can become a manager itself | live disposable experiment | partially explored: false by default; enabling it later remains unverified and is not needed for the safe baseline |
| Current Hermes can use latest MCP features | actual negotiated/client integration tests | unverified; the local Hermes 0.18.0 environment currently has legacy `mcp 1.26.0` |
| `hermes mcp test bot-factory` syntax/behavior meets intended flow | real CLI run after server exists | unverified |
| Official MCP Registry schema/version at release time | validate current schema before submission | unverified |
| `io.modelcontextprotocol/tasks` is suitable for v0.1 | stable extension plus official Python SDK and host integration | deferred: the reference extension is experimental and MCP Python SDK 2.0 does not ship its handlers |

The live spike also confirmed that the manager must remain separate from the
Hermes gateway identity: the test used an exclusive disposable manager and did
not attempt to run competing `getUpdates` consumers on one credential.

## Explicit non-goals for v0.1

- bypassing Telegram confirmation;
- BotFather-free setup of the first manager bot;
- SaaS/multi-tenant hosted factory;
- arbitrary code/templates, shell execution, or user-supplied runtime paths;
- automatic Telegram account deletion/revocation;
- direct access to private infrastructure, private repositories, or secret managers;
- a universal LLM-agent launcher;
- claiming Hermes catalog acceptance.

## Decision rule

When evidence changes a central assumption, update this file, the specification, and acceptance criteria in the same commit before broadening implementation scope.
