# Architecture and security boundaries

## Components

```text
┌───────────────────────────┐       non-secret IPC/state       ┌────────────────────────────┐
│ Hermes MCP control plane  │──────────────────────────────────▶│ Factory manager worker     │
│ short-lived stdio process │                                   │ persistent, token-bearing  │
└───────────────────────────┘                                   └──────────────┬─────────────┘
        │ safe results only                                                     │ Bot API
        ▼                                                                       ▼
   Owner sees status                                                  Telegram Managed Bots
                                                                              │ confirmed update
                                                                              ▼
                                                                  ┌─────────────────────┐
                                                                  │ SecretStore         │
                                                                  │ manager + child     │
                                                                  │ credentials         │
                                                                  └─────────┬───────────┘
                                                                            │ one child secret
                                                                            ▼
                                                            ┌─────────────────────────┐
                                                            │ Isolated child runtime  │
                                                            │ profile + local state   │
                                                            └─────────────────────────┘
```

The non-secret `BotBinding` relation maps one existing child slug to one stable
Hermes function catalog ID, profile, version, and routing namespace. MCP only
records binding intent. The persistent manager worker applies a pending binding
by updating the existing instance manifest and restarting that child when it was
active; it neither retrieves another token nor starts another Telegram consumer.

## Responsibility table

| Component | May do | Must never do |
|---|---|---|
| MCP control plane | validate non-secret intent, create request record, return status/inventory | receive a token, retain Telegram update payloads, run unbounded worker loops |
| Function catalog/binding | resolve stable IDs to built-in profiles and persist safe desired/status state | accept arbitrary prompts, tools, executable paths, or credentials |
| Manager worker | poll manager updates, match requests, retrieve child credential, materialize runtime | expose credential through status/errors, run arbitrary commands from MCP input |
| SecretStore | write/read secret by trusted internal reference | list secret contents to MCP or persist secret in SQLite/manifests |
| Instance launcher | start a known profile with a child-local environment | inherit manager/Hermes/Bitwarden credential or accept arbitrary executable/path |
| Child profile | handle its declared Telegram behavior and instance-local data | access sibling state, manager token, shell, or agent tools |

## Durable state machine

```text
pending_confirmation
  → managed_update_received
  → token_received
  → instance_materialized
  → active

any safe pre-active failure → failed
unknown/mismatch/partial external outcome → reconciliation_required
active → stopped → retired
```

State must be durable and non-secret. Every transition records timestamp, safe reason code, and correlation IDs that are not credentials. The implementation must make duplicated updates idempotent.

## Explicit handles, not transport sessions

MCP `2026-07-28` removes protocol sessions. The Factory therefore returns `request_id` on every creation request. Every future stateful tool requires that explicit handle and authorizes it for the caller. The experimental Tasks extension is not advertised in v0.1 because the official Python SDK does not yet provide a stable implementation.

## Isolation model

For local v0.1, each child has:

```text
~/.config/bot-factory/       non-secret configuration
~/.local/share/bot-factory/
  secrets/                   0700 parent
    manager-token            0600
    children/<slug>          0600
  instances/<slug>/          non-secret validated manifest
~/.local/state/bot-factory/
  factory.sqlite             0600, non-secret state
  runtime/<slug>/            0700 instance-local data
```

The exact base path is configurable by trusted local setup, not by MCP. The worker rejects symlink escape, traversal, duplicate slug overwrite, and unrecognized profile names.

## Modern MCP compatibility strategy

| Capability | Design requirement | Legacy fallback |
|---|---|---|
| Stateless core / `server/discover` | modern remote mode and tests | local stdio compatibility path |
| Tasks extension | do not advertise until its reference and Python implementation are stable and tested | `request_id` plus `factory_get_request` |
| MRTR | optional `input_required` reminder to complete Telegram confirmation | ordinary safe status/result |
| MCP Apps / subscriptions | optional profile picker/status card after host validation | complete Telegram/text UX |
| OpenTelemetry | redacted correlated traces | redacted stderr logging |

## Threat model highlights

1. **LLM exfiltration:** deny by construction; tokens are never MCP args/results.
2. **Prompt injection:** no arbitrary shell, paths, URLs, profiles, web fetches, or policy bypass through tool fields.
3. **Child-to-child leak:** unique secret and runtime boundaries; no parent environment inheritance.
4. **Duplicate/ambiguous Telegram actions:** idempotency and reconciliation, never blind retry.
5. **Public lead data:** collection notice, minimum data, owner-only access/export/purge, no data in MCP results or logs.
6. **MRTR replay/tampering:** AEAD-protected state, short TTL, request/audience and authenticated-principal binding, and server-side single use.
7. **Child inbound replay/crash:** each instance reserves update IDs before profile and Telegram effects and durably advances its offset after resolution. Completed replays are skipped. A replay of an interrupted attempt is quarantined and changes child health to `reconciliation_required` because a prior send may have succeeded; exactly-once external effects are not promised.

For implementation-level requirements, see [SPECIFICATION.md](SPECIFICATION.md) and [ACCEPTANCE.md](ACCEPTANCE.md).
