"""Persistent manager worker orchestration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from telegram_bot_factory.models import FactoryRequest, InstanceRecord, RequestState
from telegram_bot_factory.runtime import RuntimeLauncher, RuntimeProvisionError
from telegram_bot_factory.secrets import LocalFileSecretStore, SecretStoreError
from telegram_bot_factory.state import FactoryState, StateError
from telegram_bot_factory.telegram import (
    ManagedBotEvent,
    TelegramError,
    TelegramGateway,
    managed_bot_confirmation_url,
)


class WorkerError(RuntimeError):
    """Safe worker failure."""


@dataclass(frozen=True, slots=True)
class WorkerPreflight:
    manager_username: str
    can_manage_bots: bool
    secret_store_ready: bool


class ManagerWorker:
    def __init__(
        self,
        state: FactoryState,
        secrets: LocalFileSecretStore,
        telegram: TelegramGateway,
        launcher: RuntimeLauncher | None = None,
    ) -> None:
        self._state = state
        self._secrets = secrets
        self._telegram = telegram
        self._launcher = launcher

    async def preflight(self) -> WorkerPreflight:
        identity = await self._telegram.get_identity()
        self._secrets.initialize()
        if not identity.can_manage_bots:
            raise WorkerError("Bot Management Mode is disabled.")
        return WorkerPreflight(
            manager_username=identity.username,
            can_manage_bots=True,
            secret_store_ready=True,
        )

    async def notify_confirmation(self, request: FactoryRequest) -> str:
        identity = await self._telegram.get_identity()
        if not identity.can_manage_bots:
            raise WorkerError("Bot Management Mode is disabled.")
        url = managed_bot_confirmation_url(
            identity.username, request.username, request.display_name
        )
        if request.notify_owner:
            await self._telegram.send_confirmation(request.owner_telegram_id, url)
        return url

    async def poll_once(self, poll_timeout_seconds: int = 20) -> int:
        offset = self._state.polling_offset()
        events = await self._telegram.get_managed_events(offset, poll_timeout_seconds)
        for event in events:
            await self._process_event(event)
            offset = self._state.advance_polling_offset(event.update_id + 1)
        return offset

    async def dispatch_pending_notifications(self) -> None:
        for request in self._state.pending_notifications():
            try:
                await self.notify_confirmation(request)
            except TelegramError:
                self._state.record_notification_attempt(request.request_id, sent=False)
            else:
                self._state.record_notification_attempt(request.request_id, sent=True)

    async def run(self, stop: asyncio.Event, poll_timeout_seconds: int = 20) -> None:
        await self.preflight()
        while not stop.is_set():
            self._state.set_worker_heartbeat()
            try:
                await self.dispatch_pending_notifications()
                await self.poll_once(poll_timeout_seconds)
            except TelegramError:
                await asyncio.sleep(1)

    async def close(self) -> None:
        await self._telegram.close()

    async def _process_event(self, event: ManagedBotEvent) -> None:
        request = self._state.find_pending(event.child_username, event.owner_telegram_id)
        if request is None:
            await self._reconcile_unmatched(event)
            return
        if not self._state.mark_update_processed(event.update_id, request.request_id):
            current = self._state.get_request(request.request_id)
            if current is not None and current.state is RequestState.MANAGED_UPDATE_RECEIVED:
                self._state.transition(
                    request.request_id,
                    RequestState.RECONCILIATION_REQUIRED,
                    "duplicate_after_partial_processing",
                )
            return

        self._state.transition(request.request_id, RequestState.MANAGED_UPDATE_RECEIVED)
        try:
            credential = await self._telegram.get_managed_bot_token(event.child_user_id)
            self._secrets.write_child(request.slug, credential)
        except (TelegramError, SecretStoreError):
            self._state.transition(
                request.request_id,
                RequestState.RECONCILIATION_REQUIRED,
                "credential_outcome_unknown",
            )
            return
        finally:
            if "credential" in locals():
                credential = ""
        self._state.transition(request.request_id, RequestState.TOKEN_RECEIVED)
        if self._launcher is None:
            return
        try:
            self._launcher.materialize_and_start(request)
        except RuntimeProvisionError:
            self._state.transition(
                request.request_id,
                RequestState.FAILED,
                "runtime_materialization_failed",
            )
            return
        self._state.transition(request.request_id, RequestState.INSTANCE_MATERIALIZED)
        self._state.transition(request.request_id, RequestState.ACTIVE)
        self._state.upsert_instance(
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

    async def _reconcile_unmatched(self, event: ManagedBotEvent) -> None:
        self._state.record_reconciliation_event(event.update_id, "managed_update_unmatched")
        candidates = self._state.pending_for_owner(event.owner_telegram_id)
        if len(candidates) != 1:
            return
        candidate = candidates[0]
        try:
            self._state.transition(
                candidate.request_id,
                RequestState.RECONCILIATION_REQUIRED,
                "managed_update_mismatch",
            )
            self._state.mark_update_processed(event.update_id, candidate.request_id)
        except StateError:
            return
