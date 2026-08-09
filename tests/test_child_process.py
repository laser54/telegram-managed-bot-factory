from pathlib import Path

import pytest

from telegram_bot_factory.child_process import process_update
from telegram_bot_factory.profile_store import ProfileStore
from telegram_bot_factory.profiles import LeadInboxProfile


async def deliver(
    store: ProfileStore,
    profile: LeadInboxProfile,
    update_id: int,
    sender: int,
    text: str,
    send: object,
) -> str:
    return await process_update(
        store=store,
        profile=profile,
        update_id=update_id,
        sender_telegram_id=sender,
        sender_chat_id=sender,
        owner_telegram_id=42,
        text=text,
        send_message=send,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_completed_update_collision_is_a_noop(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    profile = LeadInboxProfile(42, "Notice", store)
    sent: list[tuple[int, str]] = []

    async def send(target: int, text: str) -> object:
        sent.append((target, text))
        return object()

    assert await deliver(store, profile, 1, 7, "/start", send) == "complete"
    restarted_store = ProfileStore(tmp_path)
    restarted_profile = LeadInboxProfile(42, "Notice", restarted_store)
    assert await deliver(restarted_store, restarted_profile, 1, 7, "/start", send) == "skip"
    assert len(sent) == 1


@pytest.mark.asyncio
async def test_lead_notification_crash_is_quarantined_without_duplicate(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    profile = LeadInboxProfile(42, "Notice", store)

    async def discard(target: int, text: str) -> object:
        return object()

    await deliver(store, profile, 1, 7, "/start", discard)
    await deliver(store, profile, 2, 7, "Ada", discard)
    calls = 0

    async def crash_before_owner(target: int, text: str) -> object:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated crash")
        return object()

    with pytest.raises(RuntimeError, match="simulated crash"):
        await deliver(store, profile, 3, 7, "Call me", crash_before_owner)
    assert len(store.leads()) == 1
    restarted_store = ProfileStore(tmp_path)
    restarted_profile = LeadInboxProfile(42, "Notice", restarted_store)
    assert (
        await deliver(restarted_store, restarted_profile, 3, 7, "Call me", discard)
        == "quarantine"
    )
    assert restarted_store.update_status(3) == "quarantined"
    assert len(restarted_store.leads()) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["/export confirm", "/purge confirm"])
async def test_owner_data_command_crash_is_quarantined(tmp_path: Path, command: str) -> None:
    store = ProfileStore(tmp_path)
    profile = LeadInboxProfile(42, "Notice", store)
    store.add_lead(7, "Ada", "Call me")

    async def crash_after_effect(target: int, text: str) -> object:
        raise RuntimeError("simulated crash")

    with pytest.raises(RuntimeError, match="simulated crash"):
        await deliver(store, profile, 10, 42, command, crash_after_effect)
    remaining = len(store.leads())
    restarted_store = ProfileStore(tmp_path)
    restarted_profile = LeadInboxProfile(42, "Notice", restarted_store)

    async def unexpected_send(target: int, text: str) -> object:
        raise AssertionError("ambiguous update was repeated")

    assert (
        await deliver(restarted_store, restarted_profile, 10, 42, command, unexpected_send)
        == "quarantine"
    )
    assert len(restarted_store.leads()) == remaining
    assert remaining == (1 if command.startswith("/export") else 0)


def test_update_offset_survives_restart_and_never_moves_backward(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.advance_update_offset(12)
    store.advance_update_offset(8)
    assert ProfileStore(tmp_path).update_offset() == 12


def test_incomplete_update_is_durable_reconciliation_on_restart(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    assert store.begin_update(12) == "process"
    assert ProfileStore(tmp_path).reconciliation_required() is True
