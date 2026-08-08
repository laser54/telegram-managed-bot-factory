from datetime import UTC, datetime
from pathlib import Path

import pytest

from telegram_bot_factory.config import FactoryConfig
from telegram_bot_factory.models import OwnerEchoConfig, RequestState
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.secrets import LocalFileSecretStore
from telegram_bot_factory.service import FactoryService, FactoryServiceError
from telegram_bot_factory.state import FactoryState


def ready_service(tmp_path: Path) -> FactoryService:
    paths = FactoryPaths.under(tmp_path)
    state = FactoryState(paths.database_path)
    secrets = LocalFileSecretStore(paths)
    secrets.write_manager("REDACTED_TOKEN_SHAPE")
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

