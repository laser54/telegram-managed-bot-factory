from pathlib import Path

from telegram_bot_factory.manager_cli import process_binding_commands, reconcile_child_updates
from telegram_bot_factory.models import BindingStatus, InstanceRecord, ProfileName, RequestState
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


class FakeBindingLauncher:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def stop(self, slug: object) -> None:
        self.calls.append(("stop", str(slug)))

    def rebind(self, slug: object, profile: object, config: object) -> None:
        self.calls.append(("rebind", str(slug), profile, config))

    def load_manifest(self, path: Path) -> object:
        self.calls.append(("load", path.name))
        return object()

    def start(self, manifest: object) -> None:
        self.calls.append(("start", manifest))


class FailingStartLauncher(FakeBindingLauncher):
    def start(self, manifest: object) -> None:
        del manifest
        from telegram_bot_factory.runtime import RuntimeProvisionError

        raise RuntimeProvisionError("safe failure")


def test_worker_applies_binding_without_creating_child_or_consumer(tmp_path: Path) -> None:
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
    binding = state.attach_binding(str(request.slug), "link_inbox", ProfileName.LINK_INBOX)
    launcher = FakeBindingLauncher()

    process_binding_commands(state, launcher, paths)  # type: ignore[arg-type]

    updated = state.get_binding(str(request.slug))
    assert updated is not None
    assert updated.binding_id == binding.binding_id
    assert updated.status is BindingStatus.ACTIVE
    assert state.get_instance(str(request.slug)).profile is ProfileName.LINK_INBOX  # type: ignore[union-attr]
    assert [call[0] for call in launcher.calls if isinstance(call, tuple)] == [
        "stop",
        "rebind",
        "load",
        "start",
    ]


def test_failed_rebind_does_not_leave_stopped_child_marked_active(tmp_path: Path) -> None:
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
    state.attach_binding(str(request.slug), "link_inbox", ProfileName.LINK_INBOX)

    process_binding_commands(state, FailingStartLauncher(), paths)  # type: ignore[arg-type]

    instance = state.get_instance(str(request.slug))
    binding = state.get_binding(str(request.slug))
    assert instance is not None and instance.state is RequestState.STOPPED
    assert instance.health == "failed"
    assert binding is not None and binding.status is BindingStatus.FAILED
    assert binding.safe_error == "runtime_rebind_failed"
