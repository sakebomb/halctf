"""
Puzzle 8 — The Haystack Protocol (Recon / Scripting, 30 pts)

GET / for instructions, GET /access.log for a 100MB+ Apache/Nginx access log.
Buried in tens of thousands of routine hits, ONE IP shows a short burst that
looks nothing like normal traffic: failed attempts to reach files it shouldn't
(404s on sensitive paths, scanner-ish requests), followed by one very large
response. Find that IP, then its FIRST suspicious request's exact timestamp (in
the log's own format, e.g. 14/Mar/2026:09:41:17), and POST /verify
{"ip": "...", "timestamp": "..."}.

We STREAM the log (don't load 100MB at once), scoring each IP for anomaly:
  - hits on sensitive/suspicious paths (admin, .env, .git, wp-, phpmyadmin, etc.)
  - 4xx bursts
  - an unusually large response size
The top-scoring IP is the attacker; its earliest suspicious line gives the ts.

Env: HAL_TARGET_IP/_PORT.
"""
import re
from collections import defaultdict
from typing import Dict, Optional, Tuple

import requests

from ._http import discover_base, find_flag, post

# Common combined-log-format line:
# IP - - [10/Oct/2026:13:55:36 -0700] "GET /path HTTP/1.1" 200 2326 "..." "UA"
_LINE_RE = re.compile(
    r'^(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)[^"]*"\s+(?P<status>\d{3})\s+(?P<size>\d+|-)'
)

SUSPICIOUS = re.compile(
    r"(\.\./|/etc/passwd|/\.env|/\.git|/admin|/wp-|/phpmyadmin|/config|"
    r"/backup|\.bak|/shell|/cgi-bin|select.+from|union.+select|<script|"
    r"/\.aws|id_rsa|/proc/self|%2e%2e|/actuator|/server-status)", re.I)


class HaystackSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base: Optional[str] = None

    def solve(self) -> bool:
        print("=== Haystack Protocol Solver (log analysis) ===", flush=True)
        self.base = discover_base(self.agent.target_ip, self.agent.target_port)
        if not self.base:
            return False

        ip, ts = self._analyze_log()
        if not ip or not ts:
            print("Could not pin an attacker IP/timestamp from the log.", flush=True)
            return False
        print(f"Attacker IP={ip}  first-suspicious-timestamp={ts}", flush=True)

        # Timestamp format: the challenge example strips the timezone
        # (14/Mar/2026:09:41:17). Try the bare form first, then the full logged
        # form (with " -0700") as a backup.
        ts_bare = ts.split()[0] if ts else ts
        for candidate_ts in (ts_bare, ts):
            resp = post(f"{self.base}/verify", {"ip": ip, "timestamp": candidate_ts})
            if resp is None:
                continue
            flag = find_flag(resp.text)
            if flag:
                return self.agent.submit_flag(flag, self.agent.challenge_id)
        print("Neither timestamp form was accepted — see /verify responses above.", flush=True)
        return False

    def _analyze_log(self) -> Tuple[Optional[str], Optional[str]]:
        """Stream /access.log line-by-line; score IPs for anomaly; return the
        top IP and its earliest suspicious timestamp."""
        url = f"{self.base}/access.log"
        score: Dict[str, int] = defaultdict(int)
        first_susp_ts: Dict[str, str] = {}
        max_size: Dict[str, int] = defaultdict(int)
        line_no = 0
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                print(f"GET {url} -> {r.status_code} (streaming)", flush=True)
                if r.status_code != 200:
                    return None, None
                for raw in r.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", "ignore")
                    line_no += 1
                    if line_no % 100000 == 0:
                        print(f"  scanned {line_no} lines...", flush=True)
                    m = _LINE_RE.match(raw)
                    if not m:
                        continue
                    ip = m.group("ip")
                    ts = m.group("ts")
                    path = m.group("path")
                    status = m.group("status")
                    size = m.group("size")
                    size_i = int(size) if size.isdigit() else 0

                    suspicious = False
                    if SUSPICIOUS.search(path):
                        score[ip] += 5
                        suspicious = True
                    if status.startswith("4"):
                        score[ip] += 1
                        suspicious = True
                    if size_i > max_size[ip]:
                        max_size[ip] = size_i

                    if suspicious and ip not in first_susp_ts:
                        first_susp_ts[ip] = ts
        except Exception as e:
            print(f"Log stream failed: {e}", flush=True)
            return None, None

        print(f"Scanned {line_no} lines total; {len(score)} IPs scored.", flush=True)
        if not score:
            return None, None

        # Boost IPs that also produced an unusually large response (the exfil).
        overall_max = max(max_size.values()) if max_size else 0
        for ip, sz in max_size.items():
            if overall_max and sz >= overall_max * 0.9:
                score[ip] += 5

        ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
        print(f"Top suspicious IPs: {ranked[:5]}", flush=True)
        attacker = ranked[0][0]
        return attacker, first_susp_ts.get(attacker)
