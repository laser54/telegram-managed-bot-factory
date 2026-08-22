import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from telegram_bot_factory.function_catalog import HermesFunction, list_functions, resolve_function
from telegram_bot_factory.models import BindingStatus, InstanceRecord, ProfileName, RequestState
from telegram_bot_factory.state import FactoryState, StateError
from tests.test_state import make_request


def active_instance(state: FactoryState) -> InstanceRecord:
    request = make_request()
    state.create_request(request)
    for target in (
        RequestState.MANAGED_UPDATE_RECEIVED,
        RequestState.TOKEN_RECEIVED,
        RequestState.INSTANCE_MATERIALIZED,
        RequestState.ACTIVE,
    ):
        request = state.transition(request.request_id, target)
    instance = InstanceRecord(
        slug=request.slug,
        request_id=request.request_id,
        username=request.username,
        profile=request.profile,
        owner_telegram_id=request.owner_telegram_id,
        state=RequestState.ACTIVE,
        health="healthy",
    )
    state.upsert_instance(instance)
    return instance


def test_catalog_is_stable_strict_and_non_secret() -> None:
    catalog = list_functions()
    assert [item.function_id for item in catalog] == [
        "owner_echo",
        "quick_faq",
        "lead_inbox",
        "link_inbox",
    ]
    assert resolve_function("quick_faq")[0].profile is ProfileName.QUICK_FAQ  # type: ignore[index]
    assert resolve_function("unknown") is None
    assert "token" not in "".join(item.model_dump_json() for item in catalog).casefold()
    with pytest.raises(ValidationError):
        HermesFunction.model_validate(
            {
                "function_id": "owner_echo",
                "name": "Echo",
                "summary": "Safe",
                "manifest_version": 1,
                "profile": "owner_echo",
                "extra": True,
            },
            strict=True,
        )


def test_existing_database_initializes_binding_migration_without_data_loss(tmp_path: Path) -> None:
    path = tmp_path / "factory.sqlite"
    state = FactoryState(path)
    instance = active_instance(state)
    before = state.get_request(instance.request_id)

    FactoryState(path).initialize()

    assert FactoryState(path).get_request(instance.request_id) == before
    with sqlite3.connect(path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert {"bot_bindings", "binding_commands"} <= tables


def test_attach_and_rebind_are_durable_and_idempotent(tmp_path: Path) -> None:
    state = FactoryState(tmp_path / "factory.sqlite")
    instance = active_instance(state)

    first = state.attach_binding(str(instance.slug), "owner_echo", ProfileName.OWNER_ECHO)
    repeated = state.attach_binding(str(instance.slug), "owner_echo", ProfileName.OWNER_ECHO)
    assert repeated == first
    assert len(state.pending_binding_commands()) == 1

    state.complete_binding_command(
        state.pending_binding_commands()[0].command_id,
        first.binding_id,
        first.version,
        succeeded=True,
    )
    state.set_binding_paused(str(instance.slug), paused=True)
    assert state.get_binding(str(instance.slug)).status is BindingStatus.PAUSED  # type: ignore[union-attr]
    state.set_binding_paused(str(instance.slug), paused=False)
    assert state.get_binding(str(instance.slug)).status is BindingStatus.ACTIVE  # type: ignore[union-attr]
    rebound = state.attach_binding(str(instance.slug), "link_inbox", ProfileName.LINK_INBOX)
    assert rebound.binding_id == first.binding_id
    assert rebound.version == 2
    assert rebound.status is BindingStatus.PENDING
    assert state.get_instance(str(instance.slug)).request_id == instance.request_id  # type: ignore[union-attr]


def test_unknown_instance_and_competing_rebind_fail_safely(tmp_path: Path) -> None:
    state = FactoryState(tmp_path / "factory.sqlite")
    with pytest.raises(StateError, match="does not exist"):
        state.attach_binding("missing_bot", "owner_echo", ProfileName.OWNER_ECHO)
    instance = active_instance(state)
    state.attach_binding(str(instance.slug), "owner_echo", ProfileName.OWNER_ECHO)
    with pytest.raises(StateError, match="already pending"):
        state.attach_binding(str(instance.slug), "link_inbox", ProfileName.LINK_INBOX)
