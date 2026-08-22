"""Stable non-secret Hermes function catalog backed by built-in profiles."""

from __future__ import annotations

from typing import Literal

from telegram_bot_factory.models import (
    FaqEntry,
    FunctionId,
    LeadInboxConfig,
    LinkInboxConfig,
    OwnerEchoConfig,
    ProfileConfig,
    ProfileName,
    QuickFaqConfig,
    StrictModel,
)


class HermesFunction(StrictModel):
    function_id: FunctionId
    name: str
    summary: str
    manifest_version: Literal[1] = 1
    profile: ProfileName


_FUNCTIONS: tuple[tuple[HermesFunction, ProfileConfig], ...] = (
    (
        HermesFunction(
            function_id="owner_echo",
            name="Owner Echo",
            summary="Private owner-only echo and health-check bot.",
            profile=ProfileName.OWNER_ECHO,
        ),
        OwnerEchoConfig(),
    ),
    (
        HermesFunction(
            function_id="quick_faq",
            name="Quick FAQ",
            summary="Public local FAQ menu with bounded preset answers.",
            profile=ProfileName.QUICK_FAQ,
        ),
        QuickFaqConfig(
            welcome="Welcome. Choose a frequently asked question.",
            faqs=[
                FaqEntry(question="What can this bot do?", answer="It serves this local FAQ."),
                FaqEntry(question="Does it use AI?", answer="No. Answers are deterministic."),
                FaqEntry(question="How do I get help?", answer="Use /contact."),
            ],
            contact_text="Contact the bot owner for more information.",
        ),
    ),
    (
        HermesFunction(
            function_id="lead_inbox",
            name="Lead Inbox",
            summary="Collect minimal messages locally and notify the owner.",
            profile=ProfileName.LEAD_INBOX,
        ),
        LeadInboxConfig(
            privacy_notice="Your name is optional. Your message is stored locally for the owner."
        ),
    ),
    (
        HermesFunction(
            function_id="link_inbox",
            name="Link Inbox",
            summary="Owner-only local link and note inbox without fetching URLs.",
            profile=ProfileName.LINK_INBOX,
        ),
        LinkInboxConfig(),
    ),
)


def list_functions() -> list[HermesFunction]:
    return [entry.model_copy(deep=True) for entry, _ in _FUNCTIONS]


def resolve_function(function_id: str) -> tuple[HermesFunction, ProfileConfig] | None:
    for entry, config in _FUNCTIONS:
        if entry.function_id == function_id:
            return entry.model_copy(deep=True), config.model_copy(deep=True)
    return None
