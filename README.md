# Telegram Managed Bot Factory

> A self-hosted MCP control plane and runtime for **Telegram Managed Bots**.

Configure one Telegram manager bot once. Then ask Hermes to create a focused child bot, confirm once in Telegram, and let the Factory retrieve the child credential directly from Telegram, isolate its runtime, and start a useful bot profile.

> **Status: private implementation repository; no working release yet.** The blocking Telegram Managed Bots spike passed on 2026-08-08, but no package is currently published to PyPI or the Official MCP Registry. See [docs/STATUS.md](docs/STATUS.md).

<!-- mcp-name: io.github.laser54/bot-factory -->

## Why this exists

Creating a Telegram bot normally means repeated BotFather work, manual token copying, folders, `.env` files, services, and uncertain lifecycle state. Telegram Managed Bots make a safer workflow possible:

```text
User-owned manager bot
  → owner confirms one creation in Telegram
  → Telegram sends a managed_bot update
  → Factory worker obtains the new child token directly
  → isolated child runtime starts
```

The user never pastes a child token into Hermes, a chat, or a project configuration.

This is **not** a replacement for Hermes Telegram onboarding. Hermes creates one Telegram identity for its own gateway. This project is a separate, user-owned multi-bot factory: one manager bot, many independently isolated children.

## What the first release will demonstrate

| Profile | Immediate value |
|---|---|
| `quick_faq` | A public menu FAQ bot for a service, event, portfolio, or channel. |
| `lead_inbox` | A public minimal lead-capture bot that sends a summary only to its owner. |
| `link_inbox` | An owner-only personal inbox for links and short notes. |
| `owner_echo` | An owner-only engineering smoke profile used to prove isolation and health. |

The first release deliberately does **not** create an arbitrary AI agent bot. An AI profile needs independent model credentials, cost limits, privacy policy, and a separate security review; it must never inherit Hermes or manager-bot secrets.

## Intended experience

```text
You: “Create an FAQ bot for my services: pricing, examples, contact.”

Hermes: Bot preview · quick_faq · @my_services_faq_bot
        [Create in Telegram]

You: one Telegram confirmation

Factory: receives the managed-bot event, provisions an isolated runtime

Hermes: ✅ FAQ Bot ready · Open bot
```

The goal is a 60–90 second happy path, not a terminal demo.

## Security model in one minute

- A child bot is created only after the owner's Telegram confirmation.
- Manager tokens are entered only through a local hidden `getpass` wizard, never in an MCP argument, chat, CLI argument, YAML, or shell history.
- The long-running Factory worker—not Hermes or the model—receives Telegram updates and obtains child credentials.
- Each child gets its own secret boundary, state, runtime, and least-privilege environment.
- MCP returns safe status only: no token, raw update, secret path, internal host, or unneeded identifier.
- Ambiguous external outcomes become `reconciliation_required`; the Factory never blindly creates a second bot.

Read the complete [threat model and requirements](docs/SPECIFICATION.md#11-security-requirements).

## Architecture

```text
Hermes + local MCP                 Factory worker (persistent)
------------------                 ---------------------------
create/status/inventory  ───────▶  Telegram managed_bot updates
human-friendly results             token retrieval + secret store
                                   instance materialization
                                   child lifecycle and health

                 owner confirms in Telegram
```

The MCP process may be short lived. The worker is persistent because Telegram lifecycle events must still be processed after Hermes disconnects.

## MCP 2026-07-28 baseline

The project will use the applicable modern MCP capabilities—not merely mention them:

- explicit request handles instead of protocol session state;
- strict JSON Schema 2020-12 inputs and structured outputs;
- `server/discover` and modern Streamable HTTP test coverage;
- durable `request_id` status across clients; the experimental Tasks extension is not advertised until stable Python and host support exist;
- MRTR (`input_required`) as an optional UX prompt for Telegram confirmation;
- OpenTelemetry trace propagation with redaction.

Current Hermes compatibility is a separate constraint: legacy stdio must continue to work until host capability negotiation proves a newer feature is supported. See [the protocol strategy](docs/SPECIFICATION.md#mcp-2026-07-28-progressive-modern-strategy).

## Planned install command — not available yet

```bash
uvx --from telegram-managed-bot-factory bot-factory install-hermes
```

The command above is a product requirement, **not** an instruction to run today. It will exist only after a published and verified release.

## Documentation map

Start with these documents in order:

1. **[START_HERE.md](docs/START_HERE.md)** — exact first task for the next implementation agent.
2. **[SPECIFICATION.md](docs/SPECIFICATION.md)** — complete product/UX/security/transport specification.
3. **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — component boundaries and non-negotiable invariants.
4. **[ACCEPTANCE.md](docs/ACCEPTANCE.md)** — testable v0.1 Definition of Done.
5. **[DECISIONS.md](docs/DECISIONS.md)** — decisions, evidence state, and deliberately deferred scope.
6. **[STATUS.md](docs/STATUS.md)** — repository status and publication gates.
7. **[PUBLICATION.md](docs/PUBLICATION.md)** — safe GitHub → TestPyPI → PyPI → MCP Registry release route.

## Repository status and publication plan

- **Repository:** private while the design spike and security-sensitive implementation take shape.
- **Distribution name:** `telegram-managed-bot-factory`; it returned PyPI 404 during repository bootstrap, but this is **not a reservation**. Re-check immediately before the first upload.
- **GitHub repository:** `laser54/telegram-managed-bot-factory`.
- **Future release route:** public GitHub repository → TestPyPI verification → PyPI `0.1.0` → Official MCP Registry metadata.
- **Publication authentication:** GitHub Actions OIDC Trusted Publishing, never a long-lived PyPI token in GitHub secrets.

## Contributing

The live Telegram Managed Bots spike described in [START_HERE.md](docs/START_HERE.md) has passed for the separate-manager baseline. Implementation must continue in the documented order and preserve its secret and isolation boundaries.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Sources

- [Telegram Managed Bots](https://core.telegram.org/bots/features#managed-bots)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)
- [Experimental MCP Tasks extension](https://github.com/modelcontextprotocol/ext-tasks)
