from pathlib import Path

import pytest

from telegram_bot_factory.models import (
    CreateRequest,
    FactoryRequest,
    OwnerEchoConfig,
    RequestState,
)
from telegram_bot_factory.state import FactoryState, StateError
from tests.sentinels import token_shaped_sentinel


def make_request() -> FactoryRequest:
    return FactoryRequest.from_create(
        CreateRequest(
            display_name="Owner Echo",
            username="owner_echo_bot",
            slug="owner_echo",
            profile_config=OwnerEchoConfig(),
            owner_telegram_id=42,
        )
    )


def test_request_is_durable_and_transition_is_idempotent(tmp_path: Path) -> None:
    store = FactoryState(tmp_path / "factory.sqlite")
    request = make_request()
    store.create_request(request)

    received = store.transition(request.request_id, RequestState.MANAGED_UPDATE_RECEIVED)
    duplicate = store.transition(request.request_id, RequestState.MANAGED_UPDATE_RECEIVED)

    assert received.state is RequestState.MANAGED_UPDATE_RECEIVED
    assert duplicate.state is RequestState.MANAGED_UPDATE_RECEIVED
    assert FactoryState(tmp_path / "factory.sqlite").get_request(request.request_id) == duplicate


def test_invalid_transition_is_rejected(tmp_path: Path) -> None:
    store = FactoryState(tmp_path / "factory.sqlite")
    request = make_request()
    store.create_request(request)
    with pytest.raises(StateError, match="not allowed"):
        store.transition(request.request_id, RequestState.ACTIVE)


def test_duplicate_update_has_one_effect(tmp_path: Path) -> None:
    store = FactoryState(tmp_path / "factory.sqlite")
    request = make_request()
    store.create_request(request)
    assert store.mark_update_processed(100, request.request_id) is True
    assert store.mark_update_processed(100, request.request_id) is False


def test_polling_offset_never_moves_backwards(tmp_path: Path) -> None:
    store = FactoryState(tmp_path / "factory.sqlite")
    assert store.advance_polling_offset(10) == 10
    assert store.advance_polling_offset(4) == 10
    assert FactoryState(tmp_path / "factory.sqlite").polling_offset() == 10


def test_secret_sentinel_is_absent_from_state(tmp_path: Path) -> None:
    store = FactoryState(tmp_path / "factory.sqlite")
    store.create_request(make_request())
    assert token_shaped_sentinel("TEST_SENTINEL_STATE").encode() not in (
        store.database_path.read_bytes()
    )
