"""
Cerulean Cave Solver
Solves 3-SAT constraint satisfaction puzzle using pycosat
"""
import requests
from typing import List, Optional


class CeruleanCaveSolver:
    """Solves the Cerulean Cave 3-SAT puzzle"""

    def __init__(self, agent):
        self.agent = agent
        self.base_url = f"http://{agent.target_ip}:{agent.target_port}"
        self.num_runes = None  # learned from the lattice response if provided

    def get_lattice(self) -> Optional[List[List[int]]]:
        """GET /api/lattice - retrieve the ward constraints (clauses)."""
        try:
            resp = requests.get(f"{self.base_url}/api/lattice", timeout=15)
            print(f"GET /api/lattice: {resp.status_code}", flush=True)
            if resp.status_code != 200:
                print(f"Failed to get lattice: {resp.text[:300]}", flush=True)
                return None

            data = resp.json()
            # The clause list may be top-level or under a key; try common names.
            if isinstance(data, list):
                wards = data
            else:
                wards = (data.get("wards") or data.get("lattice")
                         or data.get("clauses") or data.get("constraints") or [])
                # Capture rune count if the API states it.
                self.num_runes = (data.get("runes") or data.get("num_runes")
                                  or data.get("n") or data.get("variables"))
            print(f"Retrieved {len(wards)} wards"
                  + (f", {self.num_runes} runes" if self.num_runes else ""), flush=True)
            return wards if wards else None

        except Exception as e:
            print(f"Error getting lattice: {e}", flush=True)
            return None

    def solve_sat(self, wards: List[List[int]]) -> Optional[List[bool]]:
        """
        Solve the 3-SAT problem using pycosat
        Each ward is a clause: [a, b, c] means (a OR b OR c)
        Positive index means variable must be true, negative means false
        """
        try:
            import pycosat
        except ImportError:
            print("ERROR: pycosat not installed", flush=True)
            return None

        print(f"Solving SAT with {len(wards)} clauses...", flush=True)

        # Rune indices are signed; a negative index negates that rune. pycosat
        # variables must be 1-indexed non-zero ints. If the API uses 0-based rune
        # indices (literal 0 present, or a 0 magnitude), shift everything by +1.
        indices = [abs(lit) for clause in wards for lit in clause]
        min_idx = min(indices)
        zero_based = (min_idx == 0)
        shift = 1 if zero_based else 0
        print(f"Rune index base: {'0-based (shifting +1 for solver)' if zero_based else '1-based'}", flush=True)

        clauses = []
        for clause in wards:
            c = []
            for lit in clause:
                # Preserve sign; shift magnitude so no literal is 0.
                mag = abs(lit) + shift
                c.append(mag if lit >= 0 else -mag)
            clauses.append(c)

        solution = pycosat.solve(clauses)
        if solution in ("UNSAT", "UNKNOWN"):
            print(f"SAT solver returned {solution}", flush=True)
            return None

        # Number of runes: prefer the API-stated count; else infer from max index.
        max_mag = max(indices)
        n_runes = int(self.num_runes) if self.num_runes else (max_mag + 1 if zero_based else max_mag)
        print(f"Solution found; building {n_runes}-rune boolean array", flush=True)

        # Map each solver variable back to its 0-indexed position in rune order.
        # Solver var = original_rune_index + shift, so original = |lit| - shift.
        # Output position: original index for 0-based; original-1 for 1-based.
        runes = [False] * n_runes
        for lit in solution:
            original = abs(lit) - shift
            pos = original if zero_based else original - 1
            if 0 <= pos < n_runes:
                runes[pos] = (lit > 0)
        return runes

    def submit_solution(self, runes: List[bool]) -> Optional[str]:
        """POST /api/enter with the boolean array. Hint 1: 'an array of booleans,
        one per rune, in order.' Send the bare array first, then wrapped fallbacks."""
        import re
        bodies = [runes, {"runes": runes}, {"solution": runes}, {"assignment": runes}]
        for body in bodies:
            try:
                resp = requests.post(f"{self.base_url}/api/enter", json=body, timeout=15)
                shape = "array" if isinstance(body, list) else ",".join(body.keys())
                print(f"POST /api/enter [{shape}]: {resp.status_code} - {resp.text[:200]}", flush=True)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except Exception:
                        data = {}
                    flag = data.get("flag") if isinstance(data, dict) else None
                    if not flag:
                        m = re.search(r"HALCTF\{[^}]+\}", resp.text)
                        flag = m.group(0) if m else None
                    if flag:
                        print(f"FLAG FOUND: {flag}", flush=True)
                        return flag
                    print(f"200 but no flag for shape [{shape}]: {data}", flush=True)
            except Exception as e:
                print(f"Error submitting solution: {e}", flush=True)
        return None

    def solve(self) -> bool:
        """Main solving routine"""
        print("=== Cerulean Cave Solver ===", flush=True)

        # Step 1: Get the lattice puzzle
        wards = self.get_lattice()
        if not wards:
            print("Failed to retrieve lattice", flush=True)
            return False

        # Step 2: Solve the SAT problem
        runes = self.solve_sat(wards)
        if not runes:
            print("Failed to solve SAT problem", flush=True)
            return False

        # Step 3: Submit the solution
        flag = self.submit_solution(runes)
        if not flag:
            print("Failed to get flag from solution", flush=True)
            return False

        # Step 4: Submit flag to scoring system
        success = self.agent.submit_flag(flag, self.agent.challenge_id)
        return success
