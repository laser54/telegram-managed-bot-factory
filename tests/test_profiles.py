from telegram_bot_factory.profiles import OwnerEchoProfile


def test_owner_echo_rejects_non_owner() -> None:
    profile = OwnerEchoProfile(owner_telegram_id=42, instance_slug="owner_echo")
    assert profile.handle(7, "/health") is None


def test_owner_echo_health_is_safe() -> None:
    profile = OwnerEchoProfile(owner_telegram_id=42, instance_slug="owner_echo")
    reply = profile.handle(42, "/health")
    assert reply is not None
    assert reply.text.startswith("OK · profile=owner_echo · version=")
    assert "42" not in reply.text


def test_owner_echo_bounds_replies() -> None:
    profile = OwnerEchoProfile(owner_telegram_id=42, instance_slug="owner_echo")
    reply = profile.handle(42, "x" * 5000)
    assert reply is not None
    assert len(reply.text) <= 4012

