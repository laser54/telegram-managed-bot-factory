import json
from pathlib import Path

import pytest
from mcp import Client

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
