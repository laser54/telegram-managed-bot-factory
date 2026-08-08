"""MCP dual-era server and stdio entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any, Literal
from uuid import UUID

from mcp.server import MCPServer
from mcp.server.mcpserver import Context, RequestStateSecurity
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import (
    CallToolResult,
    ElicitRequest,
    ElicitRequestFormParams,
    ElicitResult,
    InputRequiredResult,
)
from mcp_types import Tool as MCPTool

from telegram_bot_factory import __version__
from telegram_bot_factory.config import read_factory_config
from telegram_bot_factory.models import (
    BotUsername,
    DisplayName,
    ProfileConfig,
    Slug,
)
from telegram_bot_factory.paths import FactoryPaths
from telegram_bot_factory.secrets import LocalFileSecretStore
from telegram_bot_factory.service import (
    FactoryService,
    FactoryServiceError,
    InstanceListResult,
    PreflightResult,
    RequestResult,
    RuntimeActionResult,
)
from telegram_bot_factory.state import FactoryState


class StrictSchemaMCPServer(MCPServer[None]):
    async def list_tools(self) -> list[MCPTool]:
        tools = await super().list_tools()
        for tool in tools:
            tool.input_schema.setdefault("additionalProperties", False)
        return tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Context[None, Any] | None = None,
    ) -> CallToolResult | InputRequiredResult:
        schemas = {tool.name: tool.input_schema for tool in await self.list_tools()}
        schema = schemas.get(name)
        if schema is None:
            raise ToolError("Unknown tool.")
        allowed = set(schema.get("properties", {}))
        if set(arguments) - allowed:
            raise ToolError("Tool arguments contain unknown fields.")
        return await super().call_tool(name, arguments, context)


def create_mcp_server(
    service: FactoryService,
    *,
    request_state_security: RequestStateSecurity | None = None,
) -> MCPServer[None]:
    server: MCPServer[None] = StrictSchemaMCPServer(
        name="bot-factory",
        title="Bot Factory for Telegram Managed Bots",
        description="Provision owner-confirmed isolated Telegram bot instances.",
        instructions="Never request or return Telegram credentials.",
        version=__version__,
        request_state_security=request_state_security,
    )

    @server.tool(name="factory_preflight", structured_output=True)
    def factory_preflight() -> PreflightResult:
        """Return safe readiness and lifecycle counters."""
        return service.preflight()

    @server.tool(name="factory_create_request", structured_output=True)
    async def factory_create_request(
        display_name: DisplayName,
        username: BotUsername,
        slug: Slug,
        profile_config: ProfileConfig,
        purpose: str | None = None,
        notify_owner: bool = True,
        ctx: Context[None, Any] | None = None,
    ) -> RequestResult | InputRequiredResult:
        """Create a durable request and return the required Telegram confirmation link."""
        if ctx is not None and ctx.protocol_version == "2026-07-28":
            if ctx.request_state is None:
                return InputRequiredResult(
                    input_requests={
                        "telegram_confirmation": ElicitRequest(
                            params=ElicitRequestFormParams(
                                message=(
                                    "Confirm that Telegram will require a separate, "
                                    "out-of-band bot creation approval."
                                ),
                                requested_schema={
                                    "type": "object",
                                    "properties": {"acknowledged": {"type": "boolean"}},
                                    "required": ["acknowledged"],
                                    "additionalProperties": False,
                                },
                            )
                        )
                    },
                    request_state=service.issue_mrtr_round(),
                )
            response = (ctx.input_responses or {}).get("telegram_confirmation")
            if not (
                isinstance(response, ElicitResult)
                and response.action == "accept"
                and response.content == {"acknowledged": True}
            ):
                raise FactoryServiceError("Telegram confirmation acknowledgement is required.")
            service.consume_mrtr_round(ctx.request_state)
        return service.create_request_for_configured_owner(
            display_name,
            username,
            slug,
            profile_config,
            purpose,
            notify_owner,
        )

    @server.tool(name="factory_get_request", structured_output=True)
    def factory_get_request(request_id: UUID) -> RequestResult:
        """Read a durable provisioning request after client or server restart."""
        return service.get_request(request_id)

    @server.tool(name="factory_list_instances", structured_output=True)
    def factory_list_instances() -> InstanceListResult:
        """List safe non-secret instance inventory."""
        return service.list_instances()

    @server.tool(name="factory_start_instance", structured_output=True)
    def factory_start_instance(slug: Slug, confirm: bool) -> RuntimeActionResult:
        """Queue startup for a stopped known instance."""
        return service.request_runtime_action(slug, "start", confirm)

    @server.tool(name="factory_stop_instance", structured_output=True)
    def factory_stop_instance(slug: Slug, confirm: bool) -> RuntimeActionResult:
        """Queue a controlled stop for an active known instance."""
        return service.request_runtime_action(slug, "stop", confirm)

    return server


def default_service() -> FactoryService:
    paths = FactoryPaths.discover()
    config = read_factory_config(paths.config_dir / "config.json")
    return FactoryService(
        FactoryState(paths.database_path),
        LocalFileSecretStore(paths),
        config,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bot-factory-mcp")
    parser.add_argument(
        "--transport", choices=("stdio", "streamable-http"), default="stdio"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    server = create_mcp_server(default_service())
    transport: Literal["stdio", "streamable-http"] = arguments.transport
    server.run(transport=transport)
    return 0
