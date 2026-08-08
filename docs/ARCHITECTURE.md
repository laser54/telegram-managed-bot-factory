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

## Responsibility table

| Component | May do | Must never do |
|---|---|---|
| MCP control plane | validate non-secret intent, create request record, return status/inventory | receive a token, retain Telegram update payloads, run unbounded worker loops |
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

MCP `2026-07-28` removes protocol sessions. The Factory therefore returns `request_id` on every creation request. Every future stateful tool requires that explicit handle and authorizes it for the caller. A compatible modern client may additionally receive a standard Tasks handle; it cannot be the only way to observe work.

## Isolation model

For local v0.1, each child has:

```text
factory-home/
  secrets/                 0700 parent
    manager-token           0600
    children/<slug>         0600
  state/                    0700, non-secret SQLite
  instances/<slug>/         non-secret validated manifest
  runtime/<slug>/           0700 instance-local data
```

The exact base path is configurable by trusted local setup, not by MCP. The worker rejects symlink escape, traversal, duplicate slug overwrite, and unrecognized profile names.

## Modern MCP compatibility strategy

| Capability | Design requirement | Legacy fallback |
|---|---|---|
| Stateless core / `server/discover` | modern remote mode and tests | local stdio compatibility path |
| Tasks | return/maintain standard task when client advertises extension | `request_id` plus `factory_get_request` |
| MRTR | optional `input_required` reminder to complete Telegram confirmation | ordinary safe status/result |
| MCP Apps / subscriptions | optional profile picker/status card after host validation | complete Telegram/text UX |
| OpenTelemetry | redacted correlated traces | redacted stderr logging |

## Threat model highlights

1. **LLM exfiltration:** deny by construction; tokens are never MCP args/results.
2. **Prompt injection:** no arbitrary shell, paths, URLs, profiles, web fetches, or policy bypass through tool fields.
3. **Child-to-child leak:** unique secret and runtime boundaries; no parent environment inheritance.
4. **Duplicate/ambiguous Telegram actions:** idempotency and reconciliation, never blind retry.
5. **Public lead data:** collection notice, minimum data, owner-only access/export/purge, no data in MCP results or logs.
6. **MRTR replay/tampering:** AEAD/HMAC protected state, short TTL, owner binding, request binding, and server-side single use.

For implementation-level requirements, see [SPECIFICATION.md](SPECIFICATION.md) and [ACCEPTANCE.md](ACCEPTANCE.md).
