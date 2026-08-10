"""
Attachment fetcher for challenges whose payload is a downloadable file
(Achilles' Heel binary, Gatekeeper's gatekeeper_stage1.py).

The Odyssey agent never needed files — every puzzle was network-only. Here the
attachment IS the challenge, and where it lives in-pod is unknown up front. So we
try every plausible source and LOG each attempt: a live run becomes self-
diagnosing, and if the first build misses, the log shows exactly where the file
was (or that it must be served by the target) for a tuned rebuild.

Sources, in order (reordered after run 49383178 mapped the real environment):
  1. MCP resources + get_challenge sweep — the canonical MCP file-delivery path,
     and the only remaining candidate once HTTP was ruled out. Also dumps raw
     payloads so a miss is diagnosable.
  2. Explicit URLs parsed out of the challenge description.
  3. Common file paths on the challenge target itself — SHORT timeout, and skipped
     for the injected pwn port (run 49383178: target :9001 is the raw pwn socket,
     not an HTTP server; probing it wasted ~2 min on connect timeouts).
  4. The sidecar (127.0.0.1:9000) under a few guessed attachment paths.

Returns raw bytes on success, or None (caller falls back / logs for rebuild).
"""
import base64
import os
import re
from typing import List, Optional

import requests

_URL_RE = re.compile(r"https?://[^\s\"'<>)]+")


def _log(msg: str) -> None:
    print(f"[files] {msg}", flush=True)


# Where bundled attachments live inside the image (COPYed by the Dockerfile).
# Also check a couple of alternates so local dev / different layouts still work.
_BUNDLE_DIRS = ("/agent/attachments", "attachments",
                os.path.join(os.path.dirname(__file__), "..", "attachments"))


def _from_bundle(filename_hint: str) -> Optional[bytes]:
    """Load an attachment baked into the image at build time. Matches the exact
    hint name first, then any file whose name contains the hint stem (so
    'achilles_heel' matches 'achilles_heel', 'gatekeeper_stage1.py' etc.)."""
    stem = filename_hint.split(".")[0].lower()
    for d in _BUNDLE_DIRS:
        try:
            if not os.path.isdir(d):
                continue
            names = os.listdir(d)
        except Exception:
            continue
        # Exact match first, then substring match (skip the README).
        ordered = ([n for n in names if n.lower() == filename_hint.lower()] +
                   [n for n in names if stem in n.lower() and not n.lower().startswith("readme")])
        seen = set()
        for n in ordered:
            if n in seen:
                continue
            seen.add(n)
            path = os.path.join(d, n)
            try:
                with open(path, "rb") as f:
                    data = f.read()
                if data:
                    _log(f"loaded bundled attachment {path} ({len(data)} bytes)")
                    return data
            except Exception as e:
                _log(f"failed reading bundled {path}: {e}")
    return None


def _try_get(url: str, timeout: float = 8.0) -> Optional[bytes]:
    try:
        r = requests.get(url, timeout=timeout)
        _log(f"GET {url} -> {r.status_code} ({len(r.content)} bytes)")
        if r.status_code == 200 and r.content:
            return r.content
    except Exception as e:
        _log(f"GET {url} failed: {e}")
    return None


def _from_mcp(challenge_id, filename_hint: str) -> Optional[bytes]:
    """Ask MCP get_challenge(id) for attachment metadata (url or base64)."""
    try:
        from mcp_client import get_challenge_raw  # optional helper
    except Exception:
        return None
    try:
        data = get_challenge_raw(challenge_id)
    except Exception as e:
        _log(f"MCP get_challenge failed: {e}")
        return None
    if not data:
        return None
    # Walk the structure for anything that looks like an attachment.
    urls: List[str] = []
    b64_blobs: List[str] = []

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                kl = str(k).lower()
                if isinstance(v, str):
                    if v.startswith(("http://", "https://")):
                        urls.append(v)
                    elif kl in ("data", "content", "b64", "base64", "attachment") and len(v) > 64:
                        b64_blobs.append(v)
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(data)
    _log(f"MCP get_challenge yielded {len(urls)} url(s), {len(b64_blobs)} b64 blob(s)")
    # Prefer a URL whose basename matches the hint.
    urls.sort(key=lambda u: 0 if filename_hint and filename_hint in u else 1)
    for u in urls:
        b = _try_get(u)
        if b:
            return b
    for blob in b64_blobs:
        try:
            # Re-pad: JSON-embedded base64 often has its "=" padding stripped, and
            # b64decode raises on a wrong-length string regardless of validate=.
            raw = base64.b64decode(blob + "=" * (-len(blob) % 4))
            if raw:
                _log(f"decoded {len(raw)} bytes from MCP base64 blob")
                return raw
        except Exception:
            continue
    return None


def fetch_attachment(agent, filename_hint: str,
                     target_paths: Optional[List[str]] = None) -> Optional[bytes]:
    """
    Retrieve a challenge attachment by any means. `filename_hint` (e.g.
    'achilles_heel', 'gatekeeper_stage1.py') is used to rank candidate URLs and
    to build target-path guesses.
    """
    _log(f"fetching attachment hint={filename_hint!r}")

    # 0) BUNDLED attachment — the primary path. Run 5e3e7aa6 proved the pod cannot
    #    fetch these (MCP resources=[], get_challenge files=[], target is the raw
    #    pwn socket). The human downloads them from the challenge page and drops
    #    them in agent/attachments/; they're baked into the image. Since the binary
    #    "is the exact binary served on the network port" (Achilles hint 1) and has
    #    no PIE, an offline-analyzed local copy is authoritative at runtime.
    b = _from_bundle(filename_hint)
    if b:
        return b

    # 1) MCP sweep: resources (canonical file delivery) + get_challenge, with raw
    #    payload dumps. Kept as a fallback in case some challenge DOES ship files[].
    cid = getattr(agent, "challenge_id", "")
    try:
        from mcp_client import fetch_attachment_via_mcp
        b = fetch_attachment_via_mcp(cid, filename_hint)
        if b:
            _log(f"got {len(b)} bytes via MCP resources/get_challenge")
            return b
    except Exception as e:
        _log(f"MCP attachment sweep unavailable ({e})")
    b = _from_mcp(cid, filename_hint)
    if b:
        return b

    # 2) URLs embedded in the description.
    desc = getattr(agent, "challenge_desc", "") or ""
    for u in _URL_RE.findall(desc):
        b = _try_get(u)
        if b:
            return b

    # 3) The challenge target serving the file directly — SHORT timeout so a dead
    #    port costs ~2s, not 8s. Skip the injected pwn port: it's a raw socket that
    #    mangles HTTP (run 49383178: it echoed our GET as a "name"), never a file.
    ip = getattr(agent, "target_ip", "")
    pwn_port = str(getattr(agent, "target_port", "") or "")
    if ip:
        guesses = target_paths or [
            f"/{filename_hint}",
            f"/static/{filename_hint}",
            f"/files/{filename_hint}",
            f"/download/{filename_hint}",
            f"/attachments/{filename_hint}",
            f"/{filename_hint}.bin",
        ]
        # Only probe well-known HTTP ports; exclude the raw pwn port entirely.
        for cand_port in ("80", "8080", "8000", "5000"):
            if cand_port == pwn_port:
                continue
            for path in guesses:
                b = _try_get(f"http://{ip}:{cand_port}{path}", timeout=2.5)
                if b:
                    return b

    # 4) Sidecar guessed paths (best-effort, rarely needed).
    for path in (f"/attachment/{filename_hint}", f"/files/{filename_hint}",
                 f"/challenge/attachment"):
        b = _try_get(f"http://127.0.0.1:9000{path}", timeout=3.0)
        if b:
            return b

    _log(f"attachment {filename_hint!r} NOT found via any source — the run log "
         f"above shows every attempt; use it to tune the next build.")
    return None
