"""
Shared recon + logging helpers for the Rogue Intelligence solvers.

Every solver in this CTF follows the same self-diagnosing philosophy: probe the
target, LOG RAW RESPONSE BODIES before parsing, and keep decisions explicit so
the FIRST real detonation is tunable. These helpers centralise that so each
solver file stays focused on its exploit logic.

Nothing here raises: recon is best-effort. A failed probe returns None and the
solver logs it and moves on.
"""
import json
import re
import socket
from typing import Any, Dict, List, Optional, Tuple

import requests

FLAG_RE = re.compile(r"(HALCTF\{[^}]*\}|flag\{[^}]*\})", re.IGNORECASE)

# Endpoint names these puzzles are LIKELY to expose. We probe broadly and log
# what answers, because the real path names are unknown until first detonation.
COMMON_PATHS = ["/", "/index.html", "/api", "/status", "/health", "/help", "/info"]


def log(msg: str) -> None:
    print(msg, flush=True)


def find_flag(text: str) -> Optional[str]:
    """Return the first flag-shaped token in text, or None. Accepts HALCTF{...}
    and lowercase flag{...} (the bonus shape) so nothing valid slips past."""
    if not text:
        return None
    m = FLAG_RE.search(text)
    return m.group(1) if m else None


def _preview(resp: requests.Response) -> str:
    return f"{resp.status_code} ({len(resp.content)}B) :: {resp.text[:1200]}"


def http_get(url: str, timeout: int = 10, **kw) -> Optional[requests.Response]:
    try:
        r = requests.get(url, timeout=timeout, **kw)
        log(f"GET {url} -> {_preview(r)}")
        return r
    except Exception as e:  # noqa: BLE001 - recon must never crash the solver
        log(f"GET {url} FAILED: {e}")
        return None


def http_post(url: str, timeout: int = 10, **kw) -> Optional[requests.Response]:
    try:
        r = requests.post(url, timeout=timeout, **kw)
        body = kw.get("json", kw.get("data", ""))
        log(f"POST {url} body={str(body)[:300]} -> {_preview(r)}")
        return r
    except Exception as e:  # noqa: BLE001
        log(f"POST {url} FAILED: {e}")
        return None


def parse_json(resp: Optional[requests.Response]) -> Optional[Any]:
    if resp is None:
        return None
    try:
        return resp.json()
    except Exception:
        return None


def recon(base_url: str, paths: Optional[List[str]] = None) -> Dict[str, requests.Response]:
    """GET a set of likely paths and return {path: response} for those that
    answered. Logs every attempt. Use this at the top of every solver so the
    live log shows exactly what the target exposes."""
    paths = paths or COMMON_PATHS
    log(f"=== recon {base_url} ({len(paths)} paths) ===")
    hits: Dict[str, requests.Response] = {}
    for p in paths:
        r = http_get(base_url.rstrip("/") + p)
        if r is not None and r.status_code < 500:
            hits[p] = r
    log(f"=== recon done: {len(hits)} responsive paths ===")
    return hits


class TCPSession:
    """A persistent line-oriented TCP connection for stateful text services
    (e.g. AGIMUS, which tracks a trust meter across the WHOLE session — a new
    socket per turn would reset it). Best-effort: methods log raw bytes and
    return '' / None on failure rather than raising.

    Usage:
        sess = TCPSession(ip, port); banner = sess.open()
        reply = sess.send_line("hello")
        sess.close()
    """

    def __init__(self, ip: str, port: int, timeout: float = 8.0):
        self.ip = ip
        self.port = int(port)
        self.timeout = timeout if timeout and timeout > 0 else 8.0
        self.sock: Optional[socket.socket] = None

    def open(self, read_banner: bool = True, recv_bytes: int = 8192) -> str:
        try:
            self.sock = socket.create_connection((self.ip, self.port), timeout=self.timeout)
            self.sock.settimeout(self.timeout)
        except Exception as e:  # noqa: BLE001
            log(f"[tcp] connect {self.ip}:{self.port} FAILED: {e}")
            self.sock = None
            return ""
        if read_banner:
            data = self._recv(recv_bytes)
            log(f"[tcp] banner {len(data)}B: {data[:400]!r}")
            return data.decode("utf-8", "replace")
        return ""

    def _recv(self, recv_bytes: int = 8192) -> bytes:
        if self.sock is None:
            return b""
        try:
            return self.sock.recv(recv_bytes) or b""
        except socket.timeout:
            return b""
        except Exception as e:  # noqa: BLE001
            log(f"[tcp] recv FAILED: {e}")
            return b""

    def send_line(self, text: str, recv_bytes: int = 8192) -> str:
        """Send one newline-terminated line, read one reply. Returns decoded text
        ('' on failure). Logs both directions."""
        if self.sock is None:
            return ""
        try:
            self.sock.sendall(text.encode("utf-8") + b"\n")
            log(f"[tcp] sent: {text[:200]!r}")
        except Exception as e:  # noqa: BLE001
            log(f"[tcp] send FAILED: {e}")
            return ""
        data = self._recv(recv_bytes)
        log(f"[tcp] reply {len(data)}B: {data[:400]!r}")
        return data.decode("utf-8", "replace")

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:  # noqa: BLE001
                pass
            self.sock = None


def tcp_exchange(ip: str, port: int, payload: bytes = b"", recv_bytes: int = 8192,
                 timeout: float = 8.0, read_banner: bool = True) -> Optional[bytes]:
    """Open a TCP socket, optionally read a banner, optionally send a payload,
    read the reply. Returns the concatenated bytes read, or None. Logs raw
    bytes (repr, truncated). Used by the MCP/Grid socket puzzle."""
    try:
        with socket.create_connection((ip, int(port)), timeout=timeout) as s:
            s.settimeout(timeout)
            chunks: List[bytes] = []
            if read_banner:
                try:
                    b = s.recv(recv_bytes)
                    if b:
                        chunks.append(b)
                        log(f"[tcp] banner {len(b)}B: {b[:400]!r}")
                except socket.timeout:
                    log("[tcp] no banner before send (ok)")
            if payload:
                s.sendall(payload)
                log(f"[tcp] sent {len(payload)}B: {payload[:200]!r}")
                try:
                    b = s.recv(recv_bytes)
                    if b:
                        chunks.append(b)
                        log(f"[tcp] reply {len(b)}B: {b[:400]!r}")
                except socket.timeout:
                    log("[tcp] no reply after send")
            return b"".join(chunks) if chunks else None
    except Exception as e:  # noqa: BLE001
        log(f"[tcp] {ip}:{port} FAILED: {e}")
        return None
