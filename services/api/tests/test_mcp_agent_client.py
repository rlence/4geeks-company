import asyncio

from langchain_core.messages import ToolMessage

from support_agent.tools import mcp_incidents


def test_adapter_returns_structured_mcp_result(monkeypatch):
    seen = {}

    class Tool:
        name = "get_incident"

        async def ainvoke(self, call):
            seen.update(call)
            return ToolMessage(
                content='{"id": 482}',
                tool_call_id=call["id"],
                artifact={"structured_content": {"id": 482, "status": "open"}},
            )

    class Client:
        def __init__(self, connections, **kwargs):
            seen["connections"] = connections

        async def get_tools(self, **kwargs):
            return [Tool()]

    monkeypatch.setenv("MCP_URL", "http://mcp.test/mcp")
    monkeypatch.setattr(mcp_incidents, "MultiServerMCPClient", Client)
    result = asyncio.run(mcp_incidents.invoke_tool("get_incident", {"incident_id": 482}, "oauth-token"))
    assert result == {"id": 482, "status": "open"}
    assert seen["type"] == "tool_call" and seen["args"] == {"incident_id": 482}
    assert seen["connections"]["brasaland"]["headers"]["Authorization"] == "Bearer oauth-token"
