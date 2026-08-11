# Telegram Managed Bot Factory

[![PyPI version](https://img.shields.io/pypi/v/telegram-managed-bot-factory.svg)](https://pypi.org/project/telegram-managed-bot-factory/)

<!-- mcp-name: io.github.laser54/bot-factory -->

A self-hosted MCP control plane that turns one user-owned Telegram manager bot
into isolated, useful child bots. Ask Hermes for a supported bot, confirm that
specific creation in Telegram, and the persistent Factory worker retrieves and
contains the child credential without exposing it to the model or MCP.

Version `0.1.3` adds secure Hermes Desktop first-run onboarding.
Each PyPI version is immutable; install the pinned release below.

## Install

Requires Linux with `systemd --user`, Python 3.11–3.14, [uv](https://docs.astral.sh/uv/),
Hermes 0.18, and a separate Telegram bot with Bot Management Mode enabled.

```bash
uvx --from telegram-managed-bot-factory==0.1.3 bot-factory install-hermes
```

The local installer first verifies that `systemd --user` is usable, then securely
prompts once for the manager credential, enrolls the owner, installs and verifies
the persistent user service and a fresh worker heartbeat, registers the six-tool
stdio server with Hermes, and verifies discovery. It creates no child bot.

### First connection from Hermes Desktop

A not-yet-configured Factory, or one whose mandatory user service is unhealthy, now
starts successfully instead of crashing during MCP discovery. It exposes one temporary
bootstrap tool, `factory_launch_setup`.
Hermes should call that tool rather than asking for a token. On a local Linux
desktop it opens a terminal running the complete onboarding wizard:

1. install the exact Factory version as a persistent `uv tool` (the worker unit
   never points at an evictable `uvx` cache);
2. verify `systemd --user` **before** requesting any credential;
3. accept the manager token only through hidden local terminal input;
4. enroll the owner, install the service, require it to be active, and observe a
   fresh worker heartbeat.

When the terminal reports success, reload/reconnect MCP tools. The temporary
bootstrap tool is replaced by the normal six-tool Factory catalog. The token
must never be pasted into Hermes chat, an MCP argument, or a shell command.

If Hermes Desktop is connected to a remote/headless runtime, it cannot open a
terminal on the user's laptop. Open a terminal on the Linux host that runs the
MCP and execute `bot-factory onboard`; do not send the credential through chat.
The wizard keeps failures visible when it was opened by Desktop.

## How it works

```text
You → Hermes → Factory MCP ──durable request──▶ persistent worker
                  ▲                                │
                  │ safe status                    │ Bot API
                  │                                ▼
                  └──── Telegram confirmation ◀─ manager bot
                                                   │ child credential
                                                   ▼
                                         isolated child runtime
```

Hermes and MCP are the non-secret control plane. The persistent worker alone
polls the manager bot and retrieves credentials. Each child receives only its
own credential and uses instance-local state.

## Useful profiles

| Profile | Use it for |
|---|---|
| `quick_faq` | A public menu of 3–8 local plain-text answers and contact text. |
| `lead_inbox` | A privacy-noticed message form with owner notification and confirmed export/purge. |
| `link_inbox` | Owner-only URLs and notes with `/list` and `/done`; URLs are never fetched. |

`owner_echo` is also included as an owner-only isolation and health smoke test.
Profiles cannot provide arbitrary code, executables, filesystem paths, HTML,
agent tools, or remote fetches.

## 60–90 second demo

After installation, ask Hermes:

> Create a quick FAQ bot named “Studio FAQ” with username `studio_faq_bot`.
> Welcome: “Choose a question.” Add pricing, turnaround, and contact FAQs.

Hermes returns the Telegram creation link. Open it, approve once, then open the
new child and send `/start`, `/faq 1`, and `/health`. If provisioning is still
in progress, ask Hermes for the request status. For the other profiles, submit
one test lead and try owner-only `/export confirm` then `/purge confirm`, or
save a URL in `link_inbox`, inspect `/list`, and use `/done 1`.

## Platform and boundaries

- Supported runtime: Linux with `systemd --user`; Ubuntu and WSL2 are tested.
- Supported clients: Hermes 0.18 legacy stdio and tested MCP `2026-07-28` paths.
- Not supported: Windows/macOS installation, hosted multi-tenancy, arbitrary
  child code, automatic bot-account deletion, or bypassing Telegram approval.
- The manager bot is user-owned and separate from the Hermes gateway bot.
- Every child creation requires Telegram confirmation; this is not “one-click.”
- The Official MCP Registry listing is metadata, not a security certification.

## Security highlights

- Tokens never enter MCP arguments/results, chat, CLI arguments, YAML, SQLite,
  manifests, logs, traces, fixtures, or Git.
- Secret directories are `0700`, files are `0600`, and child credentials travel
  through an inherited anonymous file descriptor rather than argv or environment.
- Child inbound update IDs and offsets are durable. Completed collisions are
  no-ops; a crash-ambiguous side effect is quarantined for reconciliation, not
  silently retried. External effects are not claimed to be exactly once.
- Inputs are bounded and validated; profiles cannot execute or fetch supplied content.

See the [security policy](SECURITY.md) and [architecture](docs/ARCHITECTURE.md)
for the full boundary model.

## Documentation and source

- [Source and issues](https://github.com/laser54/telegram-managed-bot-factory)
- [Specification](docs/SPECIFICATION.md) · [acceptance](docs/ACCEPTANCE.md) ·
  [status](docs/STATUS.md) · [publication evidence](docs/evidence/RELEASE_0.1.0_2026-08-09.md)
- [Changelog](CHANGELOG.md) · [contributing](CONTRIBUTING.md) · [security](SECURITY.md)
- [Telegram Managed Bots](https://core.telegram.org/bots/features#managed-bots) ·
  [Official MCP Registry entry](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.laser54%2Fbot-factory)

## Troubleshooting and removal

Check the worker and Hermes registration without sharing unreviewed journal output:

```bash
systemctl --user status bot-factory-manager.service
hermes mcp test bot-factory
```

On WSL2, PID 1 must be `systemd`, and the distribution must remain running.
Uninstalling the service/package does not delete Factory data or revoke Telegram
bots; review local XDG `bot-factory` directories and BotFather controls separately.
