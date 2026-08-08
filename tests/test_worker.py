from pathlib import Path

import pytest

from telegram_bot_factory.models import (
    CreateRequest,
    FactoryRequest,
    OwnerEchoConfig,
    RequestState,
)
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.secrets import LocalFileSecretStore
from telegram_bot_factory.state import FactoryState
from telegram_bot_factory.telegram import ManagedBotEvent, TelegramAmbiguousError
from telegram_bot_factory.worker import ManagerWorker
from tests.fakes import FakeRuntimeLauncher, FakeTelegramGateway


def make_worker(
    tmp_path: Path,
) -> tuple[ManagerWorker, FactoryState, LocalFileSecretStore, FakeTelegramGateway]:
    paths = FactoryPaths.under(tmp_path)
    state = FactoryState(paths.database_path)
    secrets = LocalFileSecretStore(paths)
    telegram = FakeTelegramGateway()
    return ManagerWorker(state, secrets, telegram), state, secrets, telegram


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


@pytest.mark.asyncio
async def test_confirmed_event_retrieves_and_stores_child_credential_once(tmp_path: Path) -> None:
    worker, state, secrets, telegram = make_worker(tmp_path)
    request = make_request()
    state.create_request(request)
    telegram.events = [ManagedBotEvent(10, 42, 900, "owner_echo_bot")]

    assert await worker.poll_once(poll_timeout_seconds=0) == 11
    assert state.get_request(request.request_id).state is RequestState.TOKEN_RECEIVED  # type: ignore[union-attr]
    assert secrets.child_configured(request.slug)
    assert telegram.token_calls == 1

    assert await worker.poll_once(poll_timeout_seconds=0) == 11
    assert telegram.token_calls == 1


@pytest.mark.asyncio
async def test_mismatched_update_requires_reconciliation_without_token_call(tmp_path: Path) -> None:
    worker, state, _, telegram = make_worker(tmp_path)
    request = make_request()
    state.create_request(request)
    telegram.events = [ManagedBotEvent(10, 42, 900, "different_bot")]

    await worker.poll_once(poll_timeout_seconds=0)

    assert state.get_request(request.request_id).state is RequestState.RECONCILIATION_REQUIRED  # type: ignore[union-attr]
    assert telegram.token_calls == 0
    assert state.reconciliation_event_count() == 1


@pytest.mark.asyncio
async def test_late_update_is_recorded_without_external_retry(tmp_path: Path) -> None:
    worker, state, _, telegram = make_worker(tmp_path)
    telegram.events = [ManagedBotEvent(10, 42, 900, "unknown_bot")]

    await worker.poll_once(poll_timeout_seconds=0)

    assert state.reconciliation_event_count() == 1
    assert telegram.token_calls == 0


@pytest.mark.asyncio
async def test_ambiguous_credential_result_is_not_retried(tmp_path: Path) -> None:
    worker, state, _, telegram = make_worker(tmp_path)
    request = make_request()
    state.create_request(request)
    telegram.events = [ManagedBotEvent(10, 42, 900, "owner_echo_bot")]
    telegram.credential_error = TelegramAmbiguousError("safe failure")

    await worker.poll_once(poll_timeout_seconds=0)
    await worker.poll_once(poll_timeout_seconds=0)

    assert state.get_request(request.request_id).state is RequestState.RECONCILIATION_REQUIRED  # type: ignore[union-attr]
    assert telegram.token_calls == 1


@pytest.mark.asyncio
async def test_notification_uses_managed_bot_link(tmp_path: Path) -> None:
    worker, _, _, telegram = make_worker(tmp_path)
    request = make_request()

    url = await worker.notify_confirmation(request)

    assert url.startswith("https://t.me/newbot/factory_manager_bot/owner_echo_bot?")
    assert telegram.notifications == [(42, url)]
    assert "123456789" not in url


@pytest.mark.asyncio
async def test_runtime_activation_creates_inventory_record(tmp_path: Path) -> None:
    paths = FactoryPaths.under(tmp_path)
    state = FactoryState(paths.database_path)
    secrets = LocalFileSecretStore(paths)
    telegram = FakeTelegramGateway()
    launcher = FakeRuntimeLauncher()
    worker = ManagerWorker(state, secrets, telegram, launcher)
    request = make_request()
    state.create_request(request)
    telegram.events = [ManagedBotEvent(10, 42, 900, "owner_echo_bot")]

    await worker.poll_once(poll_timeout_seconds=0)

    assert state.get_request(request.request_id).state is RequestState.ACTIVE  # type: ignore[union-attr]
    assert state.get_instance("owner_echo").health == "healthy"  # type: ignore[union-attr]
    assert launcher.requests == [request]
