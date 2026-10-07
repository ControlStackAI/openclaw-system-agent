"""Only run inside the disposable desktop VM; talks to the real MCP bridge."""
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    async with stdio_client(StdioServerParameters(command="controlstack-hypruse-mcp")) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert {"desktop", "screenshot", "pointer", "keyboard", "launch", "hypr", "clipboard"} <= tools, tools

            async def call(name, args):
                result = await session.call_tool(name, args)
                assert not result.isError, (name, result)
                return result

            state = await call("desktop", {})
            assert "ghostty" in str(state).lower(), state
            await call("pointer", {"action": "move", "x": 600, "y": 400})
            await call("keyboard", {"action": "type", "text": "printf HYPRUSE_TYPED_IN_GHOSTTY"})
            await call("keyboard", {"action": "key", "keys": "enter"})
            image = await call("screenshot", {"window": "active"})
            assert any(item.type == "image" and len(item.data) > 100 for item in image.content)
            await call("clipboard", {"action": "write", "text": "disposable-vm-clipboard"})
            assert "disposable-vm-clipboard" in str(await call("clipboard", {"action": "read"}))
            await call("hypr", {"action": "workspace", "workspace": "2"})
            await call("hypr", {"action": "workspace", "workspace": "1"})
            print(json.dumps({"hypruse_mcp": "passed", "tools": sorted(tools), "real_provider": False}))


asyncio.run(main())
