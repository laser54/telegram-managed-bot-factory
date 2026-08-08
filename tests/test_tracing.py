from pathlib import Path

import pytest
from mcp import Client
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from telegram_bot_factory.mcp_server import create_mcp_server
from tests.sentinels import token_shaped_sentinel
from tests.test_service import ready_service


@pytest.mark.asyncio
async def test_trace_context_propagates_without_arguments_or_secrets(tmp_path: Path) -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    previous = trace.get_tracer_provider()
    trace._TRACER_PROVIDER = provider  # type: ignore[attr-defined]  # isolated acceptance process
    try:
        tracer = trace.get_tracer("acceptance")
        with tracer.start_as_current_span("acceptance-parent") as parent:
            parent_trace_id = parent.get_span_context().trace_id
            async with Client(create_mcp_server(ready_service(tmp_path))) as client:
                result = await client.call_tool(
                    "factory_preflight", {"unexpected": token_shaped_sentinel("TRACE_SENTINEL")}
                )
                assert result.is_error is True
        spans = exporter.get_finished_spans()
        server_spans = [span for span in spans if span.name == "tools/call factory_preflight"]
        assert server_spans
        assert server_spans[-1].context.trace_id == parent_trace_id
        rendered = repr(
            [
                (span.name, dict(span.attributes or {}), tuple(span.events))
                for span in spans
            ]
        )
        assert "TRACE_SENTINEL" not in rendered
        assert "unexpected" not in rendered
        assert "owner_telegram_id" not in rendered
    finally:
        provider.shutdown()
        trace._TRACER_PROVIDER = previous  # type: ignore[attr-defined]
