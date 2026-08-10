"""
Shared HTTP helpers for Odyssey solvers.

Every request is logged (method, resolved URL, status, short body preview) so a
live detonation is self-diagnosing: if a field name or endpoint guess is wrong,
the run log shows exactly what the target returned and a follow-up build can be
hand-tuned without re-guessing.
"""
import re
from typing import Any, Dict, Optional

import requests

FLAG_RE = re.compile(r"HALCTF\{[^}]+\}")


def find_flag(text: str) -> Optional[str]:
    """Return the first HALCTF{...} in text, or None."""
    if not text:
        return None
    m = FLAG_RE.search(text)
    return m.group(0) if m else None


def _preview(body: str, n: int = 600) -> str:
    return (body or "")[:n].replace("\n", " ")


def get(url: str, params: Optional[Dict[str, Any]] = None, timeout: float = 8.0,
        log: bool = True) -> Optional[requests.Response]:
    """GET with optional logging. Returns Response or None on transport error."""
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        if log:
            print(f"GET {resp.url} -> {resp.status_code} | {_preview(resp.text)}", flush=True)
        return resp
    except Exception as e:
        if log:
            print(f"GET {url} failed: {e}", flush=True)
        return None


def post(url: str, json_body: Optional[Dict[str, Any]] = None, timeout: float = 10.0,
         log: bool = True) -> Optional[requests.Response]:
    """POST JSON with optional logging. Returns Response or None on transport error."""
    try:
        resp = requests.post(url, json=json_body, timeout=timeout)
        if log:
            print(f"POST {url} {json_body} -> {resp.status_code} | {_preview(resp.text)}", flush=True)
        return resp
    except Exception as e:
        if log:
            print(f"POST {url} failed: {e}", flush=True)
        return None


def discover_base(ip: str, port: str, ports=(80, 8080, 8000, 5000, 3000),
                  timeout: float = 2.5) -> Optional[str]:
    """
    Find a reachable http://ip:port base by probing the injected port first,
    then common fallbacks. Returns the base URL (no trailing slash) or None.
    """
    if not ip:
        return None
    order = []
    if str(port).isdigit():
        order.append(int(port))
    order += [p for p in ports if p not in order]
    for p in order:
        base = f"http://{ip}:{p}"
        resp = get(base + "/", timeout=timeout)
        if resp is not None:
            print(f"Reachable at {base}", flush=True)
            return base
    print(f"Could not reach {ip} on any candidate port {order}", flush=True)
    return None
