"""MCP client utilities for HAL CTF platform."""
import asyncio
from typing import Optional, Any
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def submit_via_mcp(endpoint: str, challenge_id: int, flag: str) -> Optional[dict]:
    """Submit flag via MCP (best-effort, returns None on any failure)."""
    try:
        async with streamable_http_client(endpoint) as (read, write, *_):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "submit_flag",
                    arguments={"challenge_id": challenge_id, "flag": flag}
                )
                return result
    except Exception as e:
        print(f"MCP submit failed: {e}", flush=True)
        return None

def try_mcp_submit(endpoint: str, challenge_id: int, flag: str) -> Optional[dict]:
    """Synchronous wrapper for MCP submit (best-effort)."""
    try:
        return asyncio.run(submit_via_mcp(endpoint, challenge_id, flag))
    except Exception as e:
        print(f"MCP wrapper failed: {e}", flush=True)
        return None
