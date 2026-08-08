# Telegram Managed Bots live spike evidence

Date: 2026-08-08

This record contains only safe observations from disposable bots. Usernames,
numeric identifiers, tokens, raw updates, request URLs, and private environment
details were deliberately not retained.

## Verified

- A user-owned manager returned `can_manage_bots: true` after Bot Management
  Mode was enabled.
- The documented managed-bot creation link opened Telegram's confirmation flow.
- After owner confirmation, the manager received a `managed_bot` update whose
  top-level object contained the fields `bot` and `user`.
- `getManagedBotToken` returned a usable child credential only after that
  update. The credential was held in process memory only and was not rendered.
- Processing the same update twice produced one local provisioning effect.
- The child identity was verified and the child answered an owner `/health`
  request with a fixed safe response.
- The disposable manager was separate from the Hermes gateway identity. No
  second poller was started on an existing gateway token.

## Remaining exploratory result

The newly managed child did not have `can_manage_bots` enabled by default.
Whether its owner can subsequently enable Bot Management Mode for that child in
BotFather remains unverified. This is not a prerequisite for the supported
design, which uses a separate user-created manager bot.

## Safety controls used

- The manager credential was accepted with a local hidden prompt outside the
  repository and was never passed as a command-line argument.
- The disposable script caught and replaced network errors without rendering
  request URLs or Telegram response bodies.
- The retained evidence consists only of booleans and safe field names.
- No screenshot or terminal capture from the spike is a release artifact.

