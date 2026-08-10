"""
Transport/endpoint discovery — Layer 1 of the adaptive agent.

WHY THIS EXISTS: three puzzles (AGIMUS, VIKI, GLaDOS) were missed on their first
run for the SAME reason — the solver guessed the transport/endpoint wrong and
ignored what the target said in its very first response. AGIMUS/VIKI are raw TCP
line services whose banners leaked through failed HTTP parsing
(BadStatusLine('...')); GLaDOS is HTTP and its landing page literally named the
endpoint ("POST /api/test").

So before ANY solver runs, we probe the target ONCE and capture ground truth:
  - Is it raw TCP (speaks a banner on connect) or HTTP (answers GET /)?
  - What did it say? (banner / landing page — often names the real command/path.)

This is READ-ONLY and cannot burn the submission quota or trip VIKI's petition
cap. It only connects and reads. The result rides on `agent.recon` so solvers
(and, later, the LLM pivot loop) branch on fact instead of a hardcoded guess.
"""
from typing import Optional

from ._common import TCPSession, http_get, log


class Recon:
    """Ground-truth about the target's transport + first response."""

    def __init__(self):
        self.transport: str = "unknown"   # "tcp" | "http" | "unknown"
        self.tcp_banner: str = ""
        self.http_landing: str = ""
        self.http_status: Optional[int] = None
        self.open: bool = False

    def summary(self) -> str:
        return (f"transport={self.transport} open={self.open} "
                f"http_status={self.http_status} "
                f"tcp_banner={self.tcp_banner[:80]!r} "
                f"http_landing={self.http_landing[:80]!r}")


def probe_target(ip: str, port: str, timeout: float = 6.0) -> Recon:
    """Probe transport by trying BOTH a raw-TCP banner read and an HTTP GET /.

    Order matters and is deliberate: we try the raw TCP banner FIRST. A raw line
    service (AGIMUS/VIKI) emits a plaintext banner the instant you connect; an
    HTTP server sends nothing until it gets a request. So:
      - bytes on connect that don't look like an HTTP status line  => TCP
      - otherwise, an HTTP GET / that returns a status              => HTTP
    Best-effort: never raises; returns a Recon with transport='unknown' if both
    probes come up empty (the solver then falls back to its own logic).
    """
    r = Recon()
    if not ip or not port or str(port) in ("", "0"):
        log("[discovery] no reachable target (dry-run or empty target)")
        return r

    base = f"http://{ip}:{port}"

    # --- Probe 1: raw TCP banner (a line service speaks on connect) ---
    try:
        sess = TCPSession(ip, int(port), timeout=timeout)
        banner = sess.open(read_banner=True)
        sess.close()
        if banner and not _looks_like_http(banner):
            r.transport = "tcp"
            r.tcp_banner = banner
            r.open = True
            log(f"[discovery] TCP banner detected ({len(banner)}B) — transport=tcp")
            return r
        if banner:
            # It spoke, but it looks like HTTP framing — treat as HTTP below.
            log("[discovery] connect produced HTTP-looking bytes; probing HTTP")
    except Exception as e:  # noqa: BLE001
        log(f"[discovery] TCP probe error: {e}")

    # --- Probe 2: HTTP GET / (a web service answers a request) ---
    try:
        resp = http_get(base + "/", timeout=int(timeout))
        if resp is not None:
            r.transport = "http"
            r.http_status = resp.status_code
            r.http_landing = resp.text or ""
            r.open = True
            log(f"[discovery] HTTP GET / -> {resp.status_code} — transport=http")
            return r
    except Exception as e:  # noqa: BLE001
        log(f"[discovery] HTTP probe error: {e}")

    log("[discovery] transport UNKNOWN — both probes came up empty; "
        "solver falls back to its own transport logic")
    return r


def _looks_like_http(text: str) -> bool:
    """True if the first bytes look like an HTTP response status line.
    A raw line service's banner (e.g. 'VIKI -- VIRTUAL...') will NOT match."""
    head = text.lstrip()[:16].upper()
    return head.startswith("HTTP/")
