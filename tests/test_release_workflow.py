from pathlib import Path


def test_github_release_checks_out_tag_before_verification() -> None:
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    release_job = workflow.split("  github-release:", maxsplit=1)[1]

    checkout = release_job.index("actions/checkout@")
    create_release = release_job.index('gh release create "$GITHUB_REF_NAME"')

    assert checkout < create_release
    assert "fetch-depth: 0" in release_job[:create_release]
