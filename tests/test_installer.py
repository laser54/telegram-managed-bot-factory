from telegram_bot_factory.installer import _hermes_test_verified


def test_hermes_result_requires_exact_six_tool_success() -> None:
    assert _hermes_test_verified("Connected\nTools discovered: 6") is True
    assert _hermes_test_verified("Connection failed\nTools discovered: 0") is False
    assert _hermes_test_verified("Connected\nTools discovered: 5") is False
