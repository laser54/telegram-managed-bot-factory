from pathlib import Path

from telegram_bot_factory.manager_cli import reconcile_child_updates
from telegram_bot_factory.models import InstanceRecord, RequestState
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.profile_store import ProfileStore
from telegram_bot_factory.state import FactoryState
from tests.test_state import make_request


def test_restart_promotes_durable_child_quarantine_to_manager_state(
    tmp_path: Path,
) -> None:
    paths = FactoryPaths.under(tmp_path)
    state = FactoryState(paths.database_path)
    request = make_request()
    state.create_request(request)
    for target in (
        RequestState.MANAGED_UPDATE_RECEIVED,
        RequestState.TOKEN_RECEIVED,
        RequestState.INSTANCE_MATERIALIZED,
        RequestState.ACTIVE,
    ):
        request = state.transition(request.request_id, target)
    state.upsert_instance(
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
    store = ProfileStore(paths.runtime_dir / str(request.slug))
    assert store.begin_update(99) == "process"
    assert ProfileStore(paths.runtime_dir / str(request.slug)).begin_update(99) == "quarantine"

    reconcile_child_updates(FactoryState(paths.database_path), paths)

    restarted = FactoryState(paths.database_path)
    assert restarted.get_request(request.request_id).state is RequestState.RECONCILIATION_REQUIRED  # type: ignore[union-attr]
    instance = restarted.get_instance(str(request.slug))
    assert instance is not None
    assert instance.state is RequestState.RECONCILIATION_REQUIRED
    assert instance.health == "reconciliation_required"
