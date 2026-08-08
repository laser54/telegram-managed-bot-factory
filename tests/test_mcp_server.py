import json
from pathlib import Path

import anyio
import pytest
from mcp import Client
from mcp.server.mcpserver import RequestStateSecurity
from mcp.shared.exceptions import MCPError
from mcp_types import ElicitResult, InputRequiredResult

from telegram_bot_factory.mcp_server import create_mcp_server
from tests.test_service import ready_service

EXPECTED_TOOLS = [
    "factory_preflight",
    "factory_create_request",
    "factory_get_request",
    "factory_list_instances",
    "factory_start_instance",
    "factory_stop_instance",
]

CREATE_ARGUMENTS = {
    "display_name": "Owner Echo",
    "username": "owner_echo_bot",
    "slug": "owner_echo",
    "profile_config": {"kind": "owner_echo"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_tool_catalog_is_deterministic_in_both_protocol_eras(
    tmp_path: Path, mode: str
) -> None:
    server = create_mcp_server(ready_service(tmp_path))
    async with Client(server, mode=mode) as client:  # type: ignore[arg-type]
        result = await client.list_tools()
        assert [tool.name for tool in result.tools] == EXPECTED_TOOLS
        for tool in result.tools:
            assert tool.input_schema.get("additionalProperties") is False
            assert tool.output_schema is not None
            assert tool.output_schema.get("additionalProperties") is False
            schema_text = json.dumps(tool.model_dump(mode="json")).casefold()
            assert '"token"' not in schema_text
            assert '"credential"' not in schema_text
            assert '"manager_token"' not in schema_text
            assert '"child_token"' not in schema_text
            assert '"owner_telegram_id"' not in schema_text


@pytest.mark.asyncio
async def test_preflight_returns_structured_safe_content(tmp_path: Path) -> None:
    server = create_mcp_server(ready_service(tmp_path))
    async with Client(server) as client:
        result = await client.call_tool("factory_preflight", {})
    assert result.is_error is False
    assert result.structured_content is not None
    serialized = str(result.structured_content)
    assert "TEST_SENTINEL" not in serialized
    assert "manager_user_id" not in serialized


@pytest.mark.asyncio
async def test_unknown_tool_fields_are_rejected(tmp_path: Path) -> None:
    server = create_mcp_server(ready_service(tmp_path))
    async with Client(server) as client:
        result = await client.call_tool("factory_preflight", {"unexpected": True})
    assert result.is_error is True


@pytest.mark.asyncio
async def test_modern_discovery_does_not_advertise_unimplemented_tasks(tmp_path: Path) -> None:
    async with Client(create_mcp_server(ready_service(tmp_path)), mode="auto") as client:
        discovered = client.session.discover_result
        assert discovered is not None
        assert discovered.supported_versions == ["2026-07-28"]
        assert discovered.capabilities.tasks is None
        assert discovered.capabilities.extensions is None


@pytest.mark.asyncio
async def test_modern_create_uses_sealed_single_use_mrtr_state(tmp_path: Path) -> None:
    async with Client(create_mcp_server(ready_service(tmp_path)), mode="auto") as client:
        first = await client.session.call_tool(
            "factory_create_request", CREATE_ARGUMENTS, allow_input_required=True
        )
        assert isinstance(first, InputRequiredResult)
        assert first.request_state is not None
        assert "telegram_confirmation" in (first.input_requests or {})
        response = {
            "telegram_confirmation": ElicitResult(
                action="accept", content={"acknowledged": True}
            )
        }
        completed = await client.session.call_tool(
            "factory_create_request",
            CREATE_ARGUMENTS,
            input_responses=response,
            request_state=first.request_state,
            allow_input_required=True,
        )
        assert completed.is_error is False

        replayed = await client.session.call_tool(
            "factory_create_request",
            CREATE_ARGUMENTS,
            input_responses=response,
            request_state=first.request_state,
            allow_input_required=True,
        )
        assert replayed.is_error is True
        assert "invalid or expired" in str(replayed.content).casefold()


@pytest.mark.asyncio
async def test_modern_create_rejects_tampered_sealed_state(tmp_path: Path) -> None:
    async with Client(create_mcp_server(ready_service(tmp_path)), mode="auto") as client:
        first = await client.session.call_tool(
            "factory_create_request", CREATE_ARGUMENTS, allow_input_required=True
        )
        assert isinstance(first, InputRequiredResult)
        assert first.request_state is not None
        tampered = first.request_state[:-1] + ("x" if first.request_state[-1] != "x" else "y")
        with pytest.raises(MCPError, match="Invalid or expired requestState"):
            await client.session.call_tool(
                "factory_create_request",
                CREATE_ARGUMENTS,
                input_responses={
                    "telegram_confirmation": ElicitResult(
                        action="accept", content={"acknowledged": True}
                    )
                },
                request_state=tampered,
                allow_input_required=True,
            )


@pytest.mark.asyncio
async def test_modern_create_rejects_expired_sealed_state(tmp_path: Path) -> None:
    security = RequestStateSecurity(keys=[b"e" * 32], ttl=0.01)
    server = create_mcp_server(
        ready_service(tmp_path), request_state_security=security
    )
    async with Client(server, mode="auto") as client:
        first = await client.session.call_tool(
            "factory_create_request", CREATE_ARGUMENTS, allow_input_required=True
        )
        assert isinstance(first, InputRequiredResult)
        await anyio.sleep(0.02)
        with pytest.raises(MCPError, match="Invalid or expired requestState"):
            await client.session.call_tool(
                "factory_create_request",
                CREATE_ARGUMENTS,
                input_responses={
                    "telegram_confirmation": ElicitResult(
                        action="accept", content={"acknowledged": True}
                    )
                },
                request_state=first.request_state,
                allow_input_required=True,
            )


@pytest.mark.asyncio
async def test_modern_create_binds_state_to_principal(tmp_path: Path) -> None:
    principal = ["owner-a"]
    security = RequestStateSecurity(
        keys=[b"p" * 32], bind_principal=lambda _: principal[0]
    )
    server = create_mcp_server(
        ready_service(tmp_path), request_state_security=security
    )
    async with Client(server, mode="auto") as client:
        first = await client.session.call_tool(
            "factory_create_request", CREATE_ARGUMENTS, allow_input_required=True
        )
        assert isinstance(first, InputRequiredResult)
        principal[0] = "owner-b"
        with pytest.raises(MCPError, match="Invalid or expired requestState"):
            await client.session.call_tool(
                "factory_create_request",
                CREATE_ARGUMENTS,
                input_responses={
                    "telegram_confirmation": ElicitResult(
                        action="accept", content={"acknowledged": True}
                    )
                },
                request_state=first.request_state,
                allow_input_required=True,
            )


@pytest.mark.asyncio
async def test_legacy_create_remains_single_round_trip(tmp_path: Path) -> None:
    async with Client(create_mcp_server(ready_service(tmp_path)), mode="legacy") as client:
        result = await client.call_tool("factory_create_request", CREATE_ARGUMENTS)
        assert result.is_error is False
        assert result.structured_content is not None
