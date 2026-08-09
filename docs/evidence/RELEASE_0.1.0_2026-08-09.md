# v0.1.0 publication evidence

Date: 2026-08-09

This record contains only public release identifiers and safe aggregate results.
It excludes Telegram usernames and account IDs, request IDs, credentials, raw
updates, local paths, private network details, and terminal logs.

## Public artifacts

- Public source: `https://github.com/laser54/telegram-managed-bot-factory`
- SSH-signed annotated tag: `v0.1.0`
- GitHub Release: `https://github.com/laser54/telegram-managed-bot-factory/releases/tag/v0.1.0`
- PyPI package: `telegram-managed-bot-factory==0.1.0`
- Official MCP Registry name: `io.github.laser54/bot-factory`, version `0.1.0`

The release workflow built wheel and sdist from the signed-tag commit, passed
tests, artifact/history credential-shape scans, `twine check`, and generated a
GitHub artifact attestation. The protected production environment was approved
by the maintainer, and PyPI accepted the distributions through OIDC Trusted
Publishing with digital attestations and no long-lived PyPI token.

The first `github-release` job downloaded the immutable distributions but
failed because it had no repository checkout for `gh release create
--verify-tag`. The GitHub Release was completed from that same digest-verified
workflow artifact. A pinned checkout step and regression test were then merged
in PR #13 for subsequent tags.

## Production verification

- The production PyPI JSON API returned version `0.1.0`, a wheel and sdist, the
  expected Python requirement, and no reported vulnerabilities.
- A clean production `uvx` invocation resolved and reported version `0.1.0`.
- Idempotent installation reused the existing local manager enrollment, did not
  request the credential again, and explicitly reported that it created no
  child bots.
- Hermes 0.18 connected over stdio and discovered exactly the six default
  Factory tools.
- Safe preflight returned ready and worker-healthy, with zero pending requests
  and zero reconciliation work.
- Official `mcp-publisher` 1.7.9 validated and published `server.json` after
  GitHub device authorization.
- The Official MCP Registry API returned the expected server name and version,
  PyPI identifier and version, registry type, and stdio transport.

## Documentation note

The immutable PyPI `0.1.0` long description was generated while the external
release gates were still pending, so it retains release-candidate status text.
The repository README and status documents were updated only after PyPI and
Registry verification, consistent with the project's claims discipline. A
future package version will carry the post-release wording.
