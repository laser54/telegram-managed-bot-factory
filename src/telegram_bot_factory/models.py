"""Strict non-secret domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

DisplayName = Annotated[str, StringConstraints(min_length=1, max_length=64, strip_whitespace=True)]
BotUsername = Annotated[
    str,
    StringConstraints(
        min_length=5,
        max_length=32,
        pattern=r"^[A-Za-z0-9_]+[Bb][Oo][Tt]$",
        strip_whitespace=True,
    ),
]
Slug = Annotated[
    str,
    StringConstraints(min_length=3, max_length=64, pattern=r"^[a-z][a-z0-9_]{2,63}$"),
]
FunctionId = Annotated[
    str, StringConstraints(min_length=3, max_length=64, pattern=r"^[a-z][a-z0-9_]{2,63}$")
]


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RequestState(StrEnum):
    PENDING_CONFIRMATION = "pending_confirmation"
    MANAGED_UPDATE_RECEIVED = "managed_update_received"
    TOKEN_RECEIVED = "token_received"  # noqa: S105 - lifecycle state, not a credential
    INSTANCE_MATERIALIZED = "instance_materialized"
    ACTIVE = "active"
    FAILED = "failed"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    STOPPED = "stopped"
    RETIRED = "retired"


class ProfileName(StrEnum):
    OWNER_ECHO = "owner_echo"
    QUICK_FAQ = "quick_faq"
    LEAD_INBOX = "lead_inbox"
    LINK_INBOX = "link_inbox"


class OwnerEchoConfig(StrictModel):
    kind: Literal["owner_echo"] = "owner_echo"


class FaqEntry(StrictModel):
    question: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    answer: Annotated[str, StringConstraints(min_length=1, max_length=1000)]


class QuickFaqConfig(StrictModel):
    kind: Literal["quick_faq"] = "quick_faq"
    welcome: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    faqs: Annotated[list[FaqEntry], Field(min_length=3, max_length=8)]
    contact_text: Annotated[str, StringConstraints(min_length=1, max_length=300)]


class LeadInboxConfig(StrictModel):
    kind: Literal["lead_inbox"] = "lead_inbox"
    privacy_notice: Annotated[str, StringConstraints(min_length=1, max_length=500)]


class LinkInboxConfig(StrictModel):
    kind: Literal["link_inbox"] = "link_inbox"


ProfileConfig = Annotated[
    OwnerEchoConfig | QuickFaqConfig | LeadInboxConfig | LinkInboxConfig,
    Field(discriminator="kind"),
]


class CreateRequest(StrictModel):
    display_name: DisplayName
    username: BotUsername
    slug: Slug
    profile_config: ProfileConfig
    owner_telegram_id: Annotated[int, Field(gt=0)]
    purpose: Annotated[str | None, StringConstraints(max_length=300)] = None
    notify_owner: bool = True


class FactoryRequest(StrictModel):
    request_id: UUID = Field(default_factory=uuid4)
    display_name: DisplayName
    username: BotUsername
    slug: Slug
    profile: ProfileName
    profile_config: ProfileConfig
    owner_telegram_id: Annotated[int, Field(gt=0)]
    purpose: Annotated[str | None, StringConstraints(max_length=300)] = None
    notify_owner: bool = True
    state: RequestState = RequestState.PENDING_CONFIRMATION
    safe_reason: Annotated[str | None, StringConstraints(max_length=100)] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @classmethod
    def from_create(cls, value: CreateRequest) -> FactoryRequest:
        return cls(
            display_name=value.display_name,
            username=value.username,
            slug=value.slug,
            profile=ProfileName(value.profile_config.kind),
            profile_config=value.profile_config,
            owner_telegram_id=value.owner_telegram_id,
            purpose=value.purpose,
            notify_owner=value.notify_owner,
        )


class InstanceRecord(StrictModel):
    slug: Slug
    request_id: UUID
    username: BotUsername
    profile: ProfileName
    owner_telegram_id: Annotated[int, Field(gt=0)]
    state: RequestState
    health: Literal["unknown", "healthy", "stopped", "failed", "reconciliation_required"] = (
        "unknown"
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RuntimeCommand(StrictModel):
    command_id: int = Field(gt=0)
    slug: Slug
    action: Literal["start", "stop"]


class BindingStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"


class BotBinding(StrictModel):
    binding_id: UUID = Field(default_factory=uuid4)
    slug: Slug
    function_id: FunctionId
    profile: ProfileName
    status: BindingStatus = BindingStatus.PENDING
    version: int = Field(default=1, ge=1)
    routing_namespace: Annotated[str, StringConstraints(min_length=5, max_length=80)]
    safe_error: Annotated[str | None, StringConstraints(max_length=100)] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BindingCommand(StrictModel):
    command_id: int = Field(gt=0)
    binding_id: UUID
    slug: Slug
    function_id: FunctionId
    version: int = Field(ge=1)
