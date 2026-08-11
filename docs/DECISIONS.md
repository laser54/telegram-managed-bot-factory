# Decisions, evidence, and open questions

## Decided

| Decision | Rationale |
|---|---|
| Distribution/repository name: `telegram-managed-bot-factory` | Published as public alpha `0.1.0` on PyPI; that release metadata is immutable. |
| MCP server name: `bot-factory` | Short and task-focused; it is independent of the Python distribution name. |
| Separate user-owned manager bot | Avoids conflating Hermes gateway updates with factory updates; makes ownership and runtime boundaries clear. |
| Persistent worker separate from MCP | MCP/Hermes may be transient; Telegram confirmation updates and child lifecycle are durable work. |
| Desktop first run uses a temporary bootstrap catalog | An unconfigured or unhealthy stdio server must remain discoverable without constructing the operational service. Its sole no-argument tool opens local hidden-input onboarding; it cannot accept or return a credential. After enrollment and worker verification, the normal catalog remains exactly six tools. |
| Worker executable comes from a pinned persistent `uv tool` | Registry/`uvx` MCP launch environments are cache-backed and unsuitable for a systemd `ExecStart`; onboarding installs the exact package version and uses the stable tool bin path. |
| `systemd --user` is mandatory and preflighted | The product requires a durable worker. Onboarding checks the user manager before asking for a credential, installs the unit, and verifies it is active, enabled, and reporting a fresh heartbeat; tmux/background-process fallback is not presented as successful installation. |
| WSL-compatible user-service hardening | The generated `systemd --user` unit keeps `NoNewPrivileges`, `PrivateTmp`, read-only home/system protection, and writable XDG allowlists, but omits `PrivateDevices`: that directive fails before process execution with `218/CAPABILITIES` under WSL2 user services. |
| Setup reuses a complete local enrollment | A repeated setup verifies the stored manager against Telegram without another token prompt or owner polling. A partial local setup fails closed for reconciliation instead of guessing which identity to overwrite. |
| Installation creates no child bots | Setup and Hermes registration have no child-creation side effect. A test or useful child requires a separate explicit Factory request and the normal Telegram confirmation. |
| Hermes installation verifies semantic CLI output | Hermes 0.18 can return exit status zero after an MCP connection failure, so the installer requires an explicit six-tool discovery result instead of trusting the process status alone. |
| Child token acquired only by worker after Telegram confirmation | Keeps secrets out of LLM/MCP context and removes manual copy-paste. |
| Local stdio first | Best secret boundary and simplest Hermes integration. Remote HTTP is a tested capability, not the first deployment requirement. |
| Modern MCP with compatibility fallback | Use stable 2026-07-28 core features where applicable and retain the durable `request_id` status flow across all hosts. Do not advertise the experimental Tasks extension until an official Python implementation and host support are proven. |
| No general AI child profile in v0.1 | Model secrets, costs, tools, and content policy need a separate security design. |
| Child inbound effects use durable at-most-once attempts plus quarantine | An update is reserved before profile/storage/send effects. Completed collisions are skipped; an interrupted reservation is quarantined on replay because Telegram send success can be ambiguous. Exactly-once external effects are not claimed. |
| Child reconciliation is promoted into durable Factory state | The instance-local effect ledger is authoritative; manager startup/runtime reconciliation makes the condition visible through request and instance MCP status and prevents restart from relaunching it as healthy. |
| MIT planned | Maximizes public reuse; validate final licensing and dependency compatibility before release. |

## Must be proven, not assumed

| Assumption | Required evidence | Status |
|---|---|---|
| Managed-bot manager setup works for a user-owned bot | live `getMe.can_manage_bots` | verified 2026-08-08; see `docs/evidence/TELEGRAM_SPIKE_2026-08-08.md` |
| Deep-link, update, and token retrieval match design | redacted disposable E2E | verified 2026-08-08; update fields were `bot` and `user` |
| A managed child can become a manager itself | live disposable experiment | partially explored: false by default; enabling it later remains unverified and is not needed for the safe baseline |
| Current Hermes can use latest MCP features | actual negotiated/client integration tests | legacy stdio verified with Hermes 0.18.0; modern extensions remain intentionally unclaimed |
| `hermes mcp test bot-factory` syntax/behavior meets intended flow | real CLI run after server exists | verified 2026-08-08; exactly six tools discovered |
| Official MCP Registry schema/version at release time | validate current schema before submission | `server.json` version `0.1.0` was validated and published after PyPI `0.1.0` |
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
