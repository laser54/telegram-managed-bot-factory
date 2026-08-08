# v0.1 acceptance criteria

A checkbox means **evidence exists**: automated output, a safe live result, or a reviewed artifact. A feature mentioned only in prose is not complete.

## A. Telegram foundation

- [x] A live disposable user-owned manager bot was verified with `can_manage_bots == true`.
- [x] The current managed-bot creation confirmation link was verified with Telegram.
- [x] The real `managed_bot` update was recorded as a redacted fixture/schema.
- [x] The disposable worker retrieved a child token only after owner confirmation, without a secret leak.
- [x] Duplicate/mismatched/late update paths are idempotent or enter `reconciliation_required`.
- [x] A disposable child ran and returned a safe `/health` response.

## B. Secrets and isolation

- [x] Setup accepts manager credential only via hidden local input; no CLI `--token` argument exists.
- [x] Secret directories/files have verified owner-only permissions.
- [ ] SQLite state, manifests, logs, traces, exception rendering, test output, wheel, sdist, Git history, and CI artifacts contain no secrets.
- [x] Each child process receives only its own credential; manager credential is not inherited.
- [x] Path traversal, symlink escape, duplicate slug overwrite, and arbitrary executable/profile selection are rejected.

## C. MCP product contract

- [x] Safe default allowlist is exactly `factory_preflight`, `factory_create_request`, `factory_get_request`, `factory_list_instances`, `factory_start_instance`, and `factory_stop_instance`.
- [x] Tool input/output uses strict Pydantic/JSON Schema 2020-12 models and returns structured safe status.
- [x] Creation returns durable explicit `request_id`; `factory_get_request` works after an MCP client/process restart.
- [x] Modern test client verifies `server/discover`, stateless Streamable HTTP, header validation, deterministic catalog, private cache hints, and trace redaction.
- [x] Modern test client verifies the server does not advertise the currently experimental Tasks extension; durable `request_id` authorization remains correct.
- [x] Modern test client verifies MRTR happy path plus expiry, principal mismatch, tamper, and replay rejection.
- [x] Current Hermes compatibility is demonstrated by `hermes mcp test bot-factory` and one safe `factory_preflight` call; unsupported modern features degrade gracefully.

## D. Useful child profiles

- [x] `owner_echo` proves owner-only response and isolated runtime health.
- [x] `quick_faq` launches from validated instance-local content and serves 3–8 FAQ entries with no remote fetch or HTML injection.
- [x] `lead_inbox` displays a data notice, collects minimum data, notifies only its owner, and offers owner-confirmed export/purge.
- [x] `link_inbox` is owner-only and stores links/notes without fetching/executing URLs.
- [x] Every profile returns safe `/health` and has a deterministic test suite.

## E. Operator experience

- [ ] `bot-factory install-hermes` completes user-level installation without editing Hermes YAML in the happy path.
- [ ] Setup checks manager identity, management mode, owner policy, secret store, and worker readiness before start.
- [x] A new child needs no more than one Telegram confirmation action from the owner.
- [x] Statuses are human-readable and never show raw updates, stack traces, tokens, internal paths/hosts, or unnecessary IDs.
- [ ] Main `quick_faq` demo completes in 60–90 seconds and visibly answers an FAQ question.
- [ ] README demonstrates `lead_inbox` and `link_inbox` as two additional short value scenarios.

## F. Release and publication

- [ ] `pytest`, `ruff check .`, type check, package secret scan, and dependency/security scan are green in CI.
- [x] `python -m build` produces wheel and sdist from a clean checkout; `twine check dist/*` passes.
- [ ] Clean virtual environment install works from TestPyPI before production PyPI.
- [x] Package metadata, README rendering, LICENSE, CHANGELOG, SECURITY, CONTRIBUTING, and Code of Conduct are complete.
- [ ] PyPI name is rechecked immediately before upload; prior 404 is not treated as reservation.
- [x] GitHub Actions uses PyPI Trusted Publishing OIDC with a protected environment, not a long-lived API token.
- [x] `server.json` is validated against the current Official MCP Registry schema only after real package/version values exist.
- [ ] Public release claims are made only after public GitHub source, PyPI release, and live E2E evidence exist.
