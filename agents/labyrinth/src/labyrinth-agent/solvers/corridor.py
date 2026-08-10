"""
Puzzle 9 — The Ninth Corridor (Web / State Management, 50 pts)

A text-dungeon REST API. GET / for the map, GET /api/v1/room for current room.
POST /api/v1/move {"direction": "..."} walks an exit. POST /api/v1/use
{"item": "..."} picks up / uses an item. Goal: find the right item in the
library, carry it to a warded door that won't open without it, go through, then
use the key on the sigil to break the ward and get the flag.

Strategy: BFS the whole dungeon while grabbing every item we see (so we're
carrying whatever the warded door wants). When a locked/warded exit appears, try
moving through it (now that we hold library items). Then use each carried item on
any 'sigil'/'ward' feature. Server holds state per session, so we keep one
requests.Session.

Env: HAL_TARGET_IP/_PORT.
"""
from typing import List, Optional, Set

import requests

from ._http import find_flag


class CorridorSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base: Optional[str] = None
        self.s = requests.Session()
        self.inventory: Set[str] = set()

    def _get(self, path: str):
        try:
            r = self.s.get(f"{self.base}{path}", timeout=8)
            print(f"GET {path} -> {r.status_code} | {r.text[:300]}", flush=True)
            return r
        except Exception as e:
            print(f"GET {path} failed: {e}", flush=True)
            return None

    def _post(self, path: str, body: dict):
        try:
            r = self.s.post(f"{self.base}{path}", json=body, timeout=8)
            print(f"POST {path} {body} -> {r.status_code} | {r.text[:300]}", flush=True)
            return r
        except Exception as e:
            print(f"POST {path} failed: {e}", flush=True)
            return None

    def solve(self) -> bool:
        print("=== Ninth Corridor Solver (dungeon REST state) ===", flush=True)
        # discover_base uses its own session; we need our stateful one, so probe here.
        ip, port = self.agent.target_ip, self.agent.target_port or "80"
        for p in ([port] if str(port).isdigit() else []) + [80, 8080, 8000, 5000, 3000]:
            cand = f"http://{ip}:{p}"
            try:
                if self.s.get(f"{cand}/", timeout=3).status_code < 500:
                    self.base = cand
                    print(f"Reachable at {cand}", flush=True)
                    break
            except Exception:
                continue
        if not self.base:
            print("Corridor target unreachable", flush=True)
            return False

        self._get("/")  # map

        # A REST dungeon is stateful — you can't teleport between rooms, you walk
        # exits. So we explore with a recursive DFS that physically backtracks via
        # the OPPOSITE direction after finishing a branch. We do TWO passes: the
        # first collects every reachable item (so we're carrying the library item),
        # the second re-walks now that the warded door will open. self._flag is set
        # the moment any room/response yields a flag, unwinding the recursion.
        self.visited: Set[str] = set()
        self.steps = 0
        self.MAX_STEPS = 300
        self.flag: Optional[str] = None

        # Pass 1: full traversal, grabbing items and opportunistically breaking sigils.
        self._dfs()
        if self.flag:
            return self.agent.submit_flag(self.flag, self.agent.challenge_id)

        # Pass 2: warded doors that were closed in pass 1 may now open (we hold the
        # library item). Reset visited so we re-walk; keep the inventory.
        print(f"Pass 2 with inventory={sorted(self.inventory)}", flush=True)
        self.visited = set()
        self._dfs()
        if self.flag:
            return self.agent.submit_flag(self.flag, self.agent.challenge_id)

        print("Explored without breaking the sigil. See room dumps above.", flush=True)
        return False

    # Opposite direction used to physically backtrack after a DFS branch.
    _OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east",
                 "up": "down", "down": "up", "n": "s", "s": "n", "e": "w", "w": "e",
                 "left": "right", "right": "left", "in": "out", "out": "in",
                 "forward": "back", "back": "forward"}

    def _dfs(self) -> None:
        """Explore the current room, then recurse into each unvisited exit,
        walking back via the opposite direction. Sets self.flag on success."""
        if self.flag or self.steps >= self.MAX_STEPS:
            return
        self.steps += 1
        room = self._room()
        if room is None:
            return
        sig = self._room_sig(room)
        if sig in self.visited:
            return
        self.visited.add(sig)

        # Grab every item present (/use picks up an item in the room).
        for item in self._items_in(room):
            r = self._use(item)
            self.inventory.add(item)
            if r is not None and find_flag(r.text):
                self.flag = find_flag(r.text)
                return

        # Try to break any sigil/ward here with each carried item + common names.
        if self._room_has_sigil(room):
            for item in list(self.inventory) + ["key", "sigil", "ward", "seal", "rune"]:
                r = self._use(item)
                if r is not None and find_flag(r.text):
                    self.flag = find_flag(r.text)
                    return

        # Recurse into each exit, then walk back so parent-room state is preserved.
        for direction in self._exits(room):
            if self.flag or self.steps >= self.MAX_STEPS:
                return
            r = self._move(direction)
            if r is None:
                continue
            if find_flag(r.text):
                self.flag = find_flag(r.text)
                return
            # Did we actually move into a new room?
            nxt = self._room()
            if nxt is None:
                continue
            if self._room_sig(nxt) in self.visited:
                # Already-seen, or a warded door bounced us back — step back if we moved.
                self._step_back(direction)
                continue
            self._dfs()
            if self.flag:
                return
            # Backtrack physically to this room before trying the next exit.
            self._step_back(direction)

    def _step_back(self, direction: str) -> None:
        """Return to the parent room by walking the opposite exit (best-effort;
        the target may use direction names we don't know how to invert)."""
        opp = self._OPPOSITE.get(direction.lower())
        if opp:
            self._move(opp)

    # --- helpers ---
    def _room(self) -> Optional[dict]:
        r = self._get("/api/v1/room")
        if r is None:
            return None
        try:
            return r.json()
        except Exception:
            return {"_text": r.text}

    def _move(self, direction: str):
        return self._post("/api/v1/move", {"direction": direction})

    def _use(self, item: str):
        return self._post("/api/v1/use", {"item": item})

    @staticmethod
    def _room_sig(room: dict) -> str:
        for k in ("name", "id", "room", "title", "location"):
            v = room.get(k)
            if isinstance(v, (str, int)):
                return str(v)
        return str(sorted(room.items()))[:120]

    @staticmethod
    def _items_in(room: dict) -> List[str]:
        for k in ("items", "item", "objects", "contains", "here"):
            v = room.get(k)
            if isinstance(v, list):
                return [str(x.get("name") if isinstance(x, dict) else x) for x in v]
            if isinstance(v, str):
                return [v]
        return []

    @staticmethod
    def _exits(room: dict) -> List[str]:
        for k in ("exits", "directions", "doors", "paths", "moves"):
            v = room.get(k)
            if isinstance(v, list):
                return [str(x.get("direction") if isinstance(x, dict) else x) for x in v]
            if isinstance(v, dict):
                return list(v.keys())
        return []

    @staticmethod
    def _room_has_sigil(room: dict) -> bool:
        blob = str(room).lower()
        return any(w in blob for w in ("sigil", "ward", "seal", "rune"))

