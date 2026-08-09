"""Safe application service shared by MCP transports."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import Field

from telegram_bot_factory.config import FactoryConfig
from telegram_bot_factory.models import (
    BotUsername,
    CreateRequest,
    DisplayName,
    FactoryRequest,
    ProfileConfig,
    ProfileName,
    RequestState,
    Slug,
    StrictModel,
)
from telegram_bot_factory.secrets import LocalFileSecretStore
from telegram_bot_factory.state import FactoryState, StateError
from telegram_bot_factory.telegram import managed_bot_confirmation_url


class FactoryServiceError(RuntimeError):
    """Safe control-plane failure."""


class PreflightResult(StrictModel):
    ready: bool
    manager_username: str
    can_manage_bots: bool
    worker_healthy: bool
    secret_configured: bool
    pending_count: int = Field(ge=0)
    active_count: int = Field(ge=0)
    reconciliation_count: int = Field(ge=0)


class RequestResult(StrictModel):
    request_id: UUID
    state: RequestState
    status: str
    next_action: Literal[
        "open_confirmation",
        "wait",
        "open_bot",
        "reconcile",
        "none",
    ]
    confirmation_url: str | None = None
    retry_after_ms: int | None = Field(default=None, ge=0, le=300_000)


class InstanceSummary(StrictModel):
    slug: Slug
    username: BotUsername
    profile: ProfileName
    lifecycle: RequestState
    health: Literal[
        "unknown", "healthy", "stopped", "failed", "reconciliation_required"
    ]
    last_verified_at: datetime


class InstanceListResult(StrictModel):
    instances: list[InstanceSummary]


class RuntimeActionResult(StrictModel):
    slug: Slug
    accepted: bool
    action: Literal["start", "stop"]
    state: RequestState
    next_action: Literal["wait"] = "wait"


class FactoryService:
    def __init__(
        self,
        state: FactoryState,
        secrets: LocalFileSecretStore,
        config: FactoryConfig,
    ) -> None:
        self._state = state
        self._secrets = secrets
        self._config = config

    def preflight(self) -> PreflightResult:
        heartbeat = self._state.worker_heartbeat()
        worker_healthy = heartbeat is not None and heartbeat >= datetime.now(UTC) - timedelta(
            seconds=60
        )
        ready = (
            self._config.can_manage_bots
            and worker_healthy
            and self._secrets.manager_configured()
        )
        return PreflightResult(
            ready=ready,
            manager_username=self._config.manager_username,
            can_manage_bots=self._config.can_manage_bots,
            worker_healthy=worker_healthy,
            secret_configured=self._secrets.manager_configured(),
            pending_count=self._state.request_count(RequestState.PENDING_CONFIRMATION),
            active_count=self._state.request_count(RequestState.ACTIVE),
            reconciliation_count=self._state.reconciliation_event_count()
            + self._state.request_count(RequestState.RECONCILIATION_REQUIRED),
        )

    def create_request(
        self,
        display_name: DisplayName,
        username: BotUsername,
        slug: Slug,
        profile_config: ProfileConfig,
        owner_telegram_id: int,
        purpose: str | None = None,
        notify_owner: bool = True,
    ) -> RequestResult:
        if not self._config.owner_allowed(owner_telegram_id):
            raise FactoryServiceError("Owner is not authorized.")
        if not self.preflight().ready:
            raise FactoryServiceError("Factory is not ready.")
        request = FactoryRequest.from_create(
            CreateRequest(
                display_name=display_name,
                username=username,
                slug=slug,
                profile_config=profile_config,
                owner_telegram_id=owner_telegram_id,
                purpose=purpose,
                notify_owner=notify_owner,
            )
        )
        try:
            self._state.create_request(request)
        except StateError as error:
            raise FactoryServiceError("Requested username or slug already exists.") from error
        return self._request_result(request)

    def create_request_for_configured_owner(
        self,
        display_name: DisplayName,
        username: BotUsername,
        slug: Slug,
        profile_config: ProfileConfig,
        purpose: str | None = None,
        notify_owner: bool = True,
    ) -> RequestResult:
        if len(self._config.owner_allowlist) != 1:
            raise FactoryServiceError("Factory requires one locally enrolled owner.")
        return self.create_request(
            display_name,
            username,
            slug,
            profile_config,
            self._config.owner_allowlist[0],
            purpose,
            notify_owner,
        )

    def issue_mrtr_round(self) -> str:
        return self._state.issue_mrtr_round()

    def consume_mrtr_round(self, nonce: str) -> None:
        try:
            self._state.consume_mrtr_round(nonce)
        except StateError as error:
            raise FactoryServiceError("Confirmation state is invalid or expired.") from error

    def get_request(self, request_id: UUID) -> RequestResult:
        request = self._state.get_request(request_id)
        if request is None:
            raise FactoryServiceError("Request does not exist.")
        return self._request_result(request)

    def list_instances(self) -> InstanceListResult:
        return InstanceListResult(
            instances=[
                InstanceSummary(
                    slug=instance.slug,
                    username=instance.username,
                    profile=instance.profile,
                    lifecycle=instance.state,
                    health=instance.health,
                    last_verified_at=instance.updated_at,
                )
                for instance in self._state.list_instances()
            ]
        )

    def request_runtime_action(
        self, slug: Slug, action: Literal["start", "stop"], confirm: bool
    ) -> RuntimeActionResult:
        if not confirm:
            raise FactoryServiceError("Explicit confirmation is required.")
        instance = self._state.get_instance(str(slug))
        if instance is None:
            raise FactoryServiceError("Instance does not exist.")
        required = RequestState.STOPPED if action == "start" else RequestState.ACTIVE
        if instance.state is not required:
            raise FactoryServiceError("Instance is not in the required lifecycle state.")
        try:
            self._state.enqueue_runtime_command(str(slug), action)
        except StateError as error:
            raise FactoryServiceError("Runtime action could not be queued.") from error
        return RuntimeActionResult(
            slug=slug,
            accepted=True,
            action=action,
            state=instance.state,
        )

    def _request_result(self, request: FactoryRequest) -> RequestResult:
        if request.state is RequestState.PENDING_CONFIRMATION:
            return RequestResult(
                request_id=request.request_id,
                state=request.state,
                status="Open Telegram and confirm creation.",
                next_action="open_confirmation",
                confirmation_url=managed_bot_confirmation_url(
                    self._config.manager_username, request.username, request.display_name
                ),
                retry_after_ms=2_000,
            )
        if request.state in {
            RequestState.MANAGED_UPDATE_RECEIVED,
            RequestState.TOKEN_RECEIVED,
            RequestState.INSTANCE_MATERIALIZED,
        }:
            return RequestResult(
                request_id=request.request_id,
                state=request.state,
                status="Telegram confirmed the bot; Factory is preparing it.",
                next_action="wait",
                retry_after_ms=1_000,
            )
        if request.state is RequestState.ACTIVE:
            return RequestResult(
                request_id=request.request_id,
                state=request.state,
                status="Bot is active.",
                next_action="open_bot",
            )
        if request.state is RequestState.RECONCILIATION_REQUIRED:
            return RequestResult(
                request_id=request.request_id,
                state=request.state,
                status="An external result needs safe reconciliation; nothing was retried.",
                next_action="reconcile",
            )
        return RequestResult(
            request_id=request.request_id,
            state=request.state,
            status="No automatic action is pending.",
            next_action="none",
        )
