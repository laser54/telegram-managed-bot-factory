import pytest
from pydantic import ValidationError

from telegram_bot_factory.models import CreateRequest, OwnerEchoConfig


def valid_create_request(**changes: object) -> CreateRequest:
    values: dict[str, object] = {
        "display_name": "Owner Echo",
        "username": "owner_echo_bot",
        "slug": "owner_echo",
        "profile_config": OwnerEchoConfig(),
        "owner_telegram_id": 42,
    }
    values.update(changes)
    return CreateRequest.model_validate(values)


@pytest.mark.parametrize("slug", ["../escape", "/root", "UPPER", "a", "with-dash"])
def test_slug_rejects_unsafe_values(slug: str) -> None:
    with pytest.raises(ValidationError):
        valid_create_request(slug=slug)


def test_username_must_end_in_bot() -> None:
    with pytest.raises(ValidationError):
        valid_create_request(username="unsafe_name")


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        valid_create_request(unexpected=True)

