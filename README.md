# Telegram Managed Bot Factory

> A local MCP control plane for creating owner-confirmed, isolated Telegram Managed Bots.

<!-- mcp-name: io.github.laser54/bot-factory -->

Status: v0.1.0 release candidate. The implementation and local acceptance suite are complete, but the package is not yet published to PyPI and the Registry entry is not yet live. See [project status](docs/STATUS.md).

Configure one separate manager bot once. Afterwards Hermes can request a focused child bot, you confirm its creation in Telegram, and the persistent Factory worker retrieves the child credential directly from Telegram and starts an isolated built-in profile. Child credentials never need to be copied into Hermes or a chat.

## Supported platform

- Linux with `systemd --user` (Ubuntu and WSL2 are tested development environments)
- Python 3.11–3.14
- Hermes 0.18 legacy stdio, plus modern MCP `2026-07-28` clients
- Telegram Bot API Managed Bots

Windows and macOS runtime installation are not supported in v0.1.

## Built-in profiles

| Profile | Purpose |
|---|---|
| `quick_faq` | Public welcome text and 3–8 local plain-text FAQ answers. |
| `lead_inbox` | Privacy notice, optional name and message, owner notification, confirmed `/export` and `/purge`. |
| `link_inbox` | Owner-only notes and URLs with `/list` and `/done`; URLs are never fetched. |
| `owner_echo` | Owner-only `/start`, `/help`, `/health`, and echo isolation smoke test. |

Profiles cannot supply code, executables, filesystem paths, HTML, or remote fetches.

## Install after the PyPI release

Prerequisites: install [uv](https://docs.astral.sh/uv/) and Hermes, create a dedicated manager bot in BotFather, and enable Bot Management Mode for it.

```bash
uvx --from telegram-managed-bot-factory==0.1.0 bot-factory install-hermes
```

The installer:

1. installs the pinned Factory package as a user tool;
2. asks for the manager token once through a hidden local `getpass` prompt;
3. verifies `getMe.can_manage_bots`;
4. asks you to send a one-time `/claim` command to the manager bot and locally confirm the detected account;
5. installs a hardened `bot-factory-manager.service` user unit;
6. registers `bot-factory-mcp` with Hermes and verifies all six tools.

Do not paste the token into Hermes, this README, a command argument, an environment variable, or a YAML file.
Re-running installation verifies a complete existing enrollment from the local
secret store and does not ask for the manager token again.

Before PyPI publication, contributors can run the non-live suite from source:

```bash
uv sync --frozen --group dev
uv run ruff check .
uv run mypy src
uv run pytest -q
```

## 60–90 second `quick_faq` flow

After setup, ask Hermes:

> Create a quick FAQ bot named “Studio FAQ” with username `studio_faq_bot`. Welcome text: “Choose a question.” FAQs: pricing, turnaround, and contact. Contact: “Message the owner here.”

Hermes calls `factory_create_request` and returns a Telegram confirmation URL. Open it and approve creation once. The worker receives the `managed_bot` update, retrieves the child credential, materializes its local runtime, and starts it. Open the child, select an FAQ, then send `/health`. Use `factory_get_request` or `factory_list_instances` if provisioning is still in progress.

Two other short scenarios:

- Ask for a `lead_inbox` with a concise privacy notice; submit one test lead, then use owner-only `/export` and confirmed `/purge`.
- Ask for a `link_inbox`; save a URL and note, inspect `/list`, then mark it with `/done`. The bot stores the URL but never opens it.

## MCP contract

The default catalog is exactly:

- `factory_preflight`
- `factory_create_request`
- `factory_get_request`
- `factory_list_instances`
- `factory_start_instance`
- `factory_stop_instance`

All input models reject unknown fields. Results expose lifecycle status only; they do not contain credentials, raw Telegram updates, owner IDs, local paths, or internal hosts. `request_id` is durable across MCP process restarts.

Modern clients negotiate `server/discover`, stateless Streamable HTTP, strict schemas, trace propagation, and sealed single-use MRTR state. The experimental Tasks extension is deliberately not advertised. Hermes 0.18 uses the legacy stdio fallback against the same server.

## Security boundaries

- The manager identity is user-owned and separate from the Hermes gateway bot.
- Telegram confirmation is mandatory for every child.
- The persistent worker is the only Telegram update consumer and token retriever.
- Secrets are stored under owner-only XDG directories (`0700`) and files (`0600`), outside SQLite and manifests.
- A child receives only its credential through an inherited anonymous file descriptor, never CLI arguments or environment variables.
- Duplicate updates are no-ops. Mismatched, late, or ambiguous external results enter `reconciliation_required` and are not blindly retried.

See [specification](docs/SPECIFICATION.md), [architecture](docs/ARCHITECTURE.md), [acceptance criteria](docs/ACCEPTANCE.md), and [redacted live evidence](docs/evidence/TELEGRAM_SPIKE_2026-08-08.md).

## Troubleshooting

`factory_preflight` says the worker is unhealthy:

```bash
systemctl --user status bot-factory-manager.service
journalctl --user -u bot-factory-manager.service --since today
```

On WSL2, confirm that PID 1 is `systemd` before rerunning setup:

```bash
ps -p 1 -o comm=
systemctl --user is-system-running
```

Do not paste journal output into an issue until it has been reviewed for personal data. Factory errors are intentionally redacted.

If Hermes cannot connect:

```bash
hermes mcp test bot-factory
systemctl --user restart bot-factory-manager.service
```

If user services stop after logout, enable lingering only if that matches your host policy:

```bash
loginctl enable-linger "$USER"
```

## Uninstall

```bash
systemctl --user disable --now bot-factory-manager.service
rm "$HOME/.config/systemd/user/bot-factory-manager.service"
systemctl --user daemon-reload
hermes mcp remove bot-factory
uv tool uninstall telegram-managed-bot-factory
```

Factory state and credentials are intentionally not deleted by those commands. Review the XDG `bot-factory` directories and remove them yourself only after deciding whether data must be retained. Uninstalling does not delete or revoke any Telegram bot account; use Telegram/BotFather controls separately.

## Release and Registry

Releases use GitHub OIDC Trusted Publishing with no long-lived PyPI token. The Official MCP Registry hosts metadata, not the package, and its preview listing is not a security certification. No Hermes curated-catalog listing is promised.

See [publication gates](docs/PUBLICATION.md), [changelog](CHANGELOG.md), [security policy](SECURITY.md), and [contributing guide](CONTRIBUTING.md).

## Sources

- [Telegram Managed Bots](https://core.telegram.org/bots/features#managed-bots)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)
- [Official MCP Registry publisher flow](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)
