"""VM-only stdio MCP check against a public Nix store fixture; no network needed."""
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    async with stdio_client(StdioServerParameters(command="mcp-nixos")) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert {"nix", "nix_versions"} <= tools, tools
            result = await session.call_tool("nix", {"action": "store", "type": "read", "query": sys.argv[1]})
            assert not result.isError and "MCP_NIXOS_STORE_FIXTURE" in str(result), result
            print("MCP_NIXOS_STORE_READ_PASSED")


asyncio.run(main())
