from pathlib import Path

from telegram_bot_factory.models import FaqEntry, QuickFaqConfig
from telegram_bot_factory.profile_store import ProfileStore
from telegram_bot_factory.profiles import (
    LeadInboxProfile,
    LinkInboxProfile,
    OwnerEchoProfile,
    QuickFaqProfile,
)


def test_owner_echo_rejects_non_owner() -> None:
    profile = OwnerEchoProfile(owner_telegram_id=42, instance_slug="owner_echo")
    assert profile.handle(7, "/health") == []


def test_owner_echo_health_is_safe() -> None:
    profile = OwnerEchoProfile(owner_telegram_id=42, instance_slug="owner_echo")
    replies = profile.handle(42, "/health")
    assert replies[0].text.startswith("OK · profile=owner_echo · version=")
    assert "42" not in replies[0].text


def test_owner_echo_bounds_replies() -> None:
    profile = OwnerEchoProfile(owner_telegram_id=42, instance_slug="owner_echo")
    replies = profile.handle(42, "x" * 5000)
    assert len(replies[0].text) <= 4012


def test_quick_faq_is_deterministic_and_plain_text() -> None:
    profile = QuickFaqProfile(
        QuickFaqConfig(
            welcome="Welcome <b>without markup</b>",
            faqs=[
                FaqEntry(question="One?", answer="First"),
                FaqEntry(question="Two?", answer="Second"),
                FaqEntry(question="Three?", answer="Third"),
            ],
            contact_text="Contact locally",
        )
    )
    assert "One?" in profile.handle(7, "/start")[0].text
    assert profile.handle(7, "/faq 2")[0].text == "Two?\n\nSecond"
    assert profile.handle(7, "/contact")[0].text == "Contact locally"


def test_lead_inbox_notice_collection_export_and_purge(tmp_path: Path) -> None:
    profile = LeadInboxProfile(42, "Data is stored for the owner.", ProfileStore(tmp_path))
    assert "Data is stored" in profile.handle(7, "/start")[0].text
    profile.handle(7, "Ada")
    result = profile.handle(7, "Please contact me")
    assert result[0].target == "sender"
    assert result[1].target == "owner"
    assert "Please contact me" in result[1].text
    assert "confirm" in profile.handle(42, "/export")[0].text
    assert "Ada" in profile.handle(42, "/export confirm")[0].text
    assert "confirm" in profile.handle(42, "/purge")[0].text
    assert "Purged 1" in profile.handle(42, "/purge confirm")[0].text


def test_link_inbox_is_owner_only_and_never_fetches(tmp_path: Path) -> None:
    first = LinkInboxProfile(42, ProfileStore(tmp_path / "one"))
    second = LinkInboxProfile(42, ProfileStore(tmp_path / "two"))
    assert first.handle(7, "https://example.invalid") == []
    assert "No URL was opened" in first.handle(42, "https://example.invalid")[0].text
    assert "example.invalid" in first.handle(42, "/list")[0].text
    assert second.handle(42, "/list")[0].text == "Inbox is empty."
    assert "Completed" in first.handle(42, "/done 1")[0].text
