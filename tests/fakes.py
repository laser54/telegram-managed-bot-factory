from telegram_bot_factory.telegram import ManagedBotEvent, ManagerIdentity, TelegramError


class FakeTelegramGateway:
    def __init__(self) -> None:
        self.identity = ManagerIdentity(100, "factory_manager_bot", True)
        self.events: list[ManagedBotEvent] = []
        self.credential = "REDACTED_TOKEN_SHAPE"
        self.token_calls = 0
        self.notifications: list[tuple[int, str]] = []
        self.credential_error: TelegramError | None = None

    async def get_identity(self) -> ManagerIdentity:
        return self.identity

    async def get_managed_events(
        self, offset: int, poll_timeout_seconds: int
    ) -> list[ManagedBotEvent]:
        del poll_timeout_seconds
        return [event for event in self.events if event.update_id >= offset]

    async def get_managed_bot_token(self, child_user_id: int) -> str:
        del child_user_id
        self.token_calls += 1
        if self.credential_error is not None:
            raise self.credential_error
        return self.credential

    async def send_confirmation(self, owner_telegram_id: int, confirmation_url: str) -> None:
        self.notifications.append((owner_telegram_id, confirmation_url))

    async def close(self) -> None:
        return None
