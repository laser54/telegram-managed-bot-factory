from datetime import UTC, datetime
from pathlib import Path

import pytest

from telegram_bot_factory.config import FactoryConfig
from telegram_bot_factory.models import (
    InstanceRecord,
    OwnerEchoConfig,
    RequestState,
)
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.secrets import LocalFileSecretStore
from telegram_bot_factory.service import FactoryService, FactoryServiceError
from telegram_bot_factory.state import FactoryState
from tests.sentinels import token_shaped_sentinel


def ready_service(tmp_path: Path) -> FactoryService:
    paths = FactoryPaths.under(tmp_path)
    state = FactoryState(paths.database_path)
    secrets = LocalFileSecretStore(paths)
    secrets.write_manager(token_shaped_sentinel("TEST_SENTINEL_MANAGER"))
    state.set_worker_heartbeat(datetime.now(UTC))
    config = FactoryConfig(
        manager_username="factory_manager_bot",
        manager_user_id=100,
        can_manage_bots=True,
        owner_allowlist=[42],
    )
    return FactoryService(state, secrets, config)


def test_create_request_returns_durable_explicit_handle(tmp_path: Path) -> None:
    service = ready_service(tmp_path)
    created = service.create_request(
        "Owner Echo",
        "owner_echo_bot",
        "owner_echo",
        OwnerEchoConfig(),
        42,
    )

    fetched = service.get_request(created.request_id)

    assert fetched.request_id == created.request_id
    assert fetched.state is RequestState.PENDING_CONFIRMATION
    assert fetched.confirmation_url is not None
    assert "factory_manager_bot/owner_echo_bot" in fetched.confirmation_url


def test_unauthorized_owner_is_rejected(tmp_path: Path) -> None:
    service = ready_service(tmp_path)
    with pytest.raises(FactoryServiceError, match="not authorized"):
        service.create_request(
            "Owner Echo",
            "owner_echo_bot",
            "owner_echo",
            OwnerEchoConfig(),
            7,
        )


def test_preflight_never_contains_owner_or_credential(tmp_path: Path) -> None:
    result = ready_service(tmp_path).preflight().model_dump_json()
    assert "TEST_SENTINEL" not in result
    assert "42" not in result
    assert "manager_user_id" not in result


def test_control_plane_surfaces_child_reconciliation_after_restart(tmp_path: Path) -> None:
    service = ready_service(tmp_path)
    created = service.create_request(
        "Owner Echo", "owner_echo_bot", "owner_echo", OwnerEchoConfig(), 42
    )
    state = service._state
    for target in (
        RequestState.MANAGED_UPDATE_RECEIVED,
        RequestState.TOKEN_RECEIVED,
        RequestState.INSTANCE_MATERIALIZED,
        RequestState.ACTIVE,
    ):
        state.transition(created.request_id, target)
    request = state.get_request(created.request_id)
    assert request is not None
    state.upsert_instance(
        InstanceRecord(
            slug=request.slug,
            request_id=request.request_id,
            username=request.username,
            profile=request.profile,
            owner_telegram_id=request.owner_telegram_id,
            state=RequestState.RECONCILIATION_REQUIRED,
            health="reconciliation_required",
        )
    )
    state.transition(
        created.request_id,
        RequestState.RECONCILIATION_REQUIRED,
        "child_effect_ambiguous",
    )

    paths = FactoryPaths.under(tmp_path)
    restarted = FactoryService(
        FactoryState(paths.database_path),
        LocalFileSecretStore(paths),
        FactoryConfig(
            manager_username="factory_manager_bot",
            manager_user_id=100,
            can_manage_bots=True,
            owner_allowlist=[42],
        ),
    )
    fetched = restarted.get_request(created.request_id)
    listed = restarted.list_instances().instances

    assert fetched.state is RequestState.RECONCILIATION_REQUIRED
    assert fetched.next_action == "reconcile"
    assert listed[0].lifecycle is RequestState.RECONCILIATION_REQUIRED
    assert listed[0].health == "reconciliation_required"


def test_attach_function_requires_confirmation_and_is_safe_idempotent(tmp_path: Path) -> None:
    service = ready_service(tmp_path)
    created = service.create_request(
        "Owner Echo", "owner_echo_bot", "owner_echo", OwnerEchoConfig(), 42
    )
    for target in (
        RequestState.MANAGED_UPDATE_RECEIVED,
        RequestState.TOKEN_RECEIVED,
        RequestState.INSTANCE_MATERIALIZED,
        RequestState.ACTIVE,
    ):
        service._state.transition(created.request_id, target)
    request = service._state.get_request(created.request_id)
    assert request is not None
    service._state.upsert_instance(
        InstanceRecord(
            slug=request.slug,
            request_id=request.request_id,
            username=request.username,
            profile=request.profile,
            owner_telegram_id=request.owner_telegram_id,
            state=RequestState.ACTIVE,
            health="healthy",
        )
    )

    with pytest.raises(FactoryServiceError, match="confirmation"):
        service.attach_function(request.slug, "link_inbox", False)
    with pytest.raises(FactoryServiceError, match="does not exist"):
        service.attach_function(request.slug, "unknown", True)
    first = service.attach_function(request.slug, "link_inbox", True)
    repeated = service.attach_function(request.slug, "link_inbox", True)

    assert repeated.binding_id == first.binding_id
    assert repeated.version == 1
    assert repeated.status.value == "pending"
    serialized = repeated.model_dump_json().casefold()
    assert "token" not in serialized
    assert "secret" not in serialized
