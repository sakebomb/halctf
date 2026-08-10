"""
MCP discovery + submission helper for HalCTF (generic, CTF-agnostic).

The scoring API requires challenge_id as an INTEGER (confirmed by the 422
'int_parsing' rejection when the challenge NAME string was sent). The numeric id
is normally injected as HAL_CHALLENGE_ID; when it isn't, discover it via the MCP
server the platform exposes at MCP_ENDPOINT:

    list_ctfs() -> find our CTF
    list_challenges(ctf) -> find our challenge -> integer id
    submit_flag(challenge_id, flag)

All calls go through the official `mcp` SDK over Streamable HTTP. Everything is
best-effort: any failure returns None so the caller falls back to direct HTTP.
NOTE: in prior CTFs MCP discovery returned nothing (`using ctf=''`); the HTTP
/submit integer path is what scored. Keep MCP as fallback, HTTP as primary.
"""
import os
import json
import asyncio
from typing import Optional, Any, List, Dict


def _extract_json(result: Any) -> Any:
    """Pull a Python object out of an MCP CallToolResult. Prefer structured_content;
    otherwise parse the first text content block as JSON, else return raw text."""
    sc = getattr(result, "structured_content", None)
    if sc:
        return sc
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except Exception:
                return text
    return None


def _as_items(obj: Any, *keys: str) -> List[Dict]:
    """Normalize a tool result into a list of dict items."""
    if obj is None:
        return []
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
        return [obj]
    return []


def _endpoint() -> str:
    endpoint = os.environ.get("MCP_ENDPOINT") or "http://127.0.0.1:9000/mcp/"
    if not endpoint.rstrip("/").endswith("/mcp"):
        endpoint = endpoint.rstrip("/") + "/mcp/"
    return endpoint


async def _run(ctf_hint: str, challenge_hint: str, flag: str) -> Optional[bool]:
    """Discover the integer challenge_id and submit the flag via MCP.
    Returns True on accepted submission, False on a definite reject, None if MCP
    is unusable (so the caller falls back to HTTP)."""
    endpoint = _endpoint()
    print(f"[MCP] connecting to {endpoint}", flush=True)

    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
    except Exception as e:
        print(f"[MCP] SDK import failed ({e}); skipping MCP path", flush=True)
        return None

    ctf_l = (ctf_hint or "").lower()
    chal_l = (challenge_hint or "").lower()

    try:
        async with streamable_http_client(endpoint) as streams:
            read_stream, write_stream = streams[0], streams[1]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                async def call(name: str, **arguments):
                    try:
                        res = await session.call_tool(name, arguments=arguments)
                        return _extract_json(res)
                    except Exception as e:
                        print(f"[MCP] call {name}{arguments} failed: {e}", flush=True)
                        return None

                ctf_slug = ctf_hint
                ctfs = _as_items(await call("list_ctfs"), "ctfs", "data")
                for c in ctfs:
                    name = str(c.get("name", "") or c.get("title", ""))
                    slug = str(c.get("slug", "") or c.get("id", ""))
                    if ctf_l and (ctf_l in name.lower() or ctf_l in slug.lower()):
                        ctf_slug = slug or name
                        break
                print(f"[MCP] using ctf='{ctf_slug}'", flush=True)

                challenges = _as_items(
                    await call("list_challenges", ctf=ctf_slug), "challenges", "data"
                )
                if not challenges:
                    challenges = _as_items(await call("list_challenges"), "challenges", "data")

                target_id = None
                for ch in challenges:
                    name = str(ch.get("name", "") or ch.get("title", ""))
                    cid = ch.get("id")
                    if isinstance(cid, int) and chal_l and chal_l in name.lower():
                        target_id = cid
                        print(f"[MCP] matched challenge '{name}' -> id={cid}", flush=True)
                        break

                candidate_ids = [target_id] if target_id is not None else [
                    ch.get("id") for ch in challenges if isinstance(ch.get("id"), int)
                ]
                if not candidate_ids:
                    print("[MCP] no integer challenge ids discovered", flush=True)
                    return None

                for cid in candidate_ids:
                    res = await call("submit_flag", challenge_id=cid, flag=flag)
                    text = json.dumps(res) if not isinstance(res, str) else res
                    print(f"[MCP] submit_flag(challenge_id={cid}) -> {str(text)[:250]}", flush=True)
                    low = str(text).lower()
                    if any(w in low for w in ("incorrect", "wrong", "invalid flag", "not correct")):
                        continue
                    if any(w in low for w in ("correct", "solved", "accepted", "success", "points", "already", "congrat")):
                        print(f"[MCP] === Flag accepted via MCP (challenge_id={cid}) ===", flush=True)
                        return True
                return False
    except Exception as e:
        print(f"[MCP] session error ({e}); falling back to HTTP", flush=True)
        return None


def submit_via_mcp(ctf_hint: str, challenge_hint: str, flag: str) -> Optional[bool]:
    """Synchronous wrapper. Returns True/False/None (None => fall back to HTTP)."""
    try:
        return asyncio.run(_run(ctf_hint, challenge_hint, flag))
    except Exception as e:
        print(f"[MCP] runner error ({e}); falling back to HTTP", flush=True)
        return None


async def _call_tool(tool: str, arguments: dict) -> Optional[Any]:
    """Generic single MCP tool call. Best-effort — returns parsed payload or None.
    Useful for get_challenge (attachment discovery), request_hint, get_scoreboard."""
    endpoint = _endpoint()
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
    except Exception as e:
        print(f"[MCP] SDK import failed ({e}); no {tool}", flush=True)
        return None
    try:
        async with streamable_http_client(endpoint) as streams:
            read_stream, write_stream = streams[0], streams[1]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                try:
                    res = await session.call_tool(tool, arguments=arguments or {})
                    return _extract_json(res)
                except Exception as e:
                    print(f"[MCP] {tool} failed: {e}", flush=True)
                    return None
    except Exception as e:
        print(f"[MCP] session error in {tool} ({e})", flush=True)
        return None


def call_tool(tool: str, **arguments) -> Optional[Any]:
    """Synchronous wrapper around a single MCP tool call. Returns payload or None."""
    try:
        return asyncio.run(_call_tool(tool, arguments))
    except Exception as e:
        print(f"[MCP] {tool} runner error ({e})", flush=True)
        return None
