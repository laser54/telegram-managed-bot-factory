from pathlib import Path

import httpx
import pytest

from telegram_bot_factory.mcp_server import create_mcp_server
from tests.test_service import ready_service

MODERN_META = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "acceptance-test", "version": "1"},
}


@pytest.mark.asyncio
async def test_stateless_http_discovery_and_routing_headers(tmp_path: Path) -> None:
    app = create_mcp_server(ready_service(tmp_path)).streamable_http_app(
        stateless_http=True,
        json_response=True,
        host="127.0.0.1",
    )
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "server/discover",
        "params": {"_meta": MODERN_META},
    }
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:8000"
        ) as client:
            accepted = await client.post(
                "/mcp",
                json=body,
                headers={
                    "Accept": "application/json",
                    "MCP-Protocol-Version": "2026-07-28",
                    "Mcp-Method": "server/discover",
                },
            )
            assert accepted.status_code == 200
            assert accepted.headers.get("Mcp-Session-Id") is None
            result = accepted.json()["result"]
            assert result["supportedVersions"] == ["2026-07-28"]
            assert result["capabilities"].get("tasks") is None

            mismatched = await client.post(
                "/mcp",
                json=body,
                headers={
                    "Accept": "application/json",
                    "MCP-Protocol-Version": "2026-07-28",
                    "Mcp-Method": "tools/list",
                },
            )
            assert mismatched.status_code == 400
            assert mismatched.json()["error"]["code"] == -32020

            missing_envelope = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "server/discover",
                    "params": {},
                },
                headers={
                    "Accept": "application/json",
                    "MCP-Protocol-Version": "2026-07-28",
                    "Mcp-Method": "server/discover",
                },
            )
            assert missing_envelope.status_code == 400
            assert "params._meta" in missing_envelope.json()["error"]["message"]
