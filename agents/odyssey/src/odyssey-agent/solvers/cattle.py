"""
Puzzle 4 — The Cattle of Helios (Recon / Adversarial Oracle, 125 pts)

Thirty beasts; some are the Sun's (immortal), some mortal. A herdsman answers
GET /api/ask/<id> with a verdict, but lies on 1 answer in 3, INDEPENDENTLY each
time (not consistently per beast). So the truth for a beast = majority verdict
over many independent asks.

At p=1/3 lie rate, ~40 reads/beast still fails the full 30-count ~1/3 of the
time; ~100 reads/beast pushes to >99%. We sample ~120/beast for margin.

POST /api/slaughter {"mortal": [ids...]} takes the non-Sun beasts. A wrong
slaughter is refused and reports HOW MANY were miscounted (never which), so on
refusal we resample every beast deeper and retry. The flag is in the success
response.

Env: HAL_TARGET_IP/_PORT.
"""
from collections import Counter
from typing import Dict, List, Optional

from ._http import discover_base, find_flag, get, post

SAMPLES_PER_BEAST = 120       # first pass; >99% for 30 beasts at 1/3 lie rate
RESAMPLE_EXTRA = 160          # deeper pass after a refusal


class CattleSolver:
    def __init__(self, agent):
        self.agent = agent
        self.base: Optional[str] = None

    def solve(self) -> bool:
        print("=== Cattle of Helios Solver (majority-vote oracle) ===", flush=True)
        self.base = discover_base(self.agent.target_ip, self.agent.target_port)
        if not self.base:
            return False

        ids = self._get_herd()
        if not ids:
            print("Could not read the herd tally", flush=True)
            return False
        print(f"Herd: {len(ids)} beasts -> {ids}", flush=True)

        # Accumulate verdict counts per beast across passes so resampling adds to
        # (rather than replaces) prior evidence.
        counts: Dict[int, Counter] = {i: Counter() for i in ids}

        self._sample_all(ids, counts, SAMPLES_PER_BEAST)
        mortal = self._majority_mortal(ids, counts)
        print(f"Pass 1 majority-mortal ({len(mortal)}): {mortal}", flush=True)

        resp = self._slaughter(mortal)
        flag = self._flag_from(resp)
        if flag:
            return self.agent.submit_flag(flag, self.agent.challenge_id)

        # Refused: resample deeper and retry a few times. Each retry adds more
        # reads to the weakest evidence, flipping the borderline beasts.
        for attempt in range(3):
            miscount = self._miscount_from(resp)
            print(f"Slaughter refused (miscount≈{miscount}); resampling deeper "
                  f"(attempt {attempt + 1})", flush=True)
            self._sample_all(ids, counts, RESAMPLE_EXTRA)
            mortal = self._majority_mortal(ids, counts)
            print(f"Retry majority-mortal ({len(mortal)}): {mortal}", flush=True)
            resp = self._slaughter(mortal)
            flag = self._flag_from(resp)
            if flag:
                return self.agent.submit_flag(flag, self.agent.challenge_id)

        print("Cattle not solved after resampling; see verdict tallies above.", flush=True)
        return False

    # ---- herd + oracle -----------------------------------------------------

    def _get_herd(self) -> List[int]:
        resp = get(f"{self.base}/api/herd")
        if resp is None:
            return []
        try:
            data = resp.json()
        except Exception:
            return []
        # Accept {"herd":[...]}/{"cattle":[...]}/{"ids":[...]}/{"count":30} or a list.
        items = None
        if isinstance(data, dict):
            for k in ("herd", "cattle", "beasts", "ids", "animals", "data"):
                if isinstance(data.get(k), list):
                    items = data[k]
                    break
            if items is None and isinstance(data.get("count"), int):
                return list(range(data["count"]))
        elif isinstance(data, list):
            items = data
        if items is None:
            return []
        ids = []
        for it in items:
            if isinstance(it, int):
                ids.append(it)
            elif isinstance(it, dict):
                v = it.get("id")
                if isinstance(v, int):
                    ids.append(v)
                elif isinstance(v, str) and v.isdigit():
                    ids.append(int(v))
            elif isinstance(it, str) and it.isdigit():
                ids.append(int(it))
        return ids

    def _ask(self, beast_id: int) -> Optional[str]:
        """One ask; returns normalized verdict 'mortal' / 'immortal' / None."""
        resp = get(f"{self.base}/api/ask/{beast_id}", log=False)
        if resp is None or resp.status_code != 200:
            return None
        text = resp.text.lower()
        try:
            obj = resp.json()
            if isinstance(obj, dict):
                for k in ("verdict", "answer", "result", "kind", "type", "status"):
                    if isinstance(obj.get(k), str):
                        text = obj[k].lower()
                        break
                # boolean shape {"mortal": true}
                if isinstance(obj.get("mortal"), bool):
                    return "mortal" if obj["mortal"] else "immortal"
                if isinstance(obj.get("immortal"), bool):
                    return "immortal" if obj["immortal"] else "mortal"
        except Exception:
            pass
        if "immortal" in text or "sun" in text or "sacred" in text or "divine" in text:
            return "immortal"
        if "mortal" in text or "ordinary" in text or "beast" in text:
            return "mortal"
        return None

    def _sample_all(self, ids: List[int], counts: Dict[int, Counter], n: int):
        total = len(ids) * n
        print(f"Sampling {n} reads x {len(ids)} beasts = {total} asks...", flush=True)
        done = 0
        for i in ids:
            none_here = 0
            for _ in range(n):
                v = self._ask(i)
                if v:
                    counts[i][v] += 1
                else:
                    counts[i]["_none"] += 1  # unparseable/failed ask — tracked, not silently dropped
                    none_here += 1
                done += 1
            # Heartbeat: keep stdout alive (2-min silence kills the agent). Warn
            # loudly if too many asks for this beast failed to parse — otherwise a
            # beast with all-None verdicts silently defaults to 'immortal'.
            if none_here > n * 0.25:
                print(f"  !! beast {i}: {none_here}/{n} asks unparseable — verdict "
                      f"unreliable (raw: {dict(counts[i])})", flush=True)
            else:
                print(f"  beast {i}: {dict(counts[i])} ({done}/{total} asks)", flush=True)

    @staticmethod
    def _majority_mortal(ids: List[int], counts: Dict[int, Counter]) -> List[int]:
        """
        A beast is mortal iff its majority VALID verdict is 'mortal'. A beast with
        no valid verdicts at all is a red flag — we default it to immortal (safest:
        keeps the Sun's cattle intact) but it will show in the miscount if wrong,
        prompting a deeper resample rather than a silent miss.
        """
        mortal = []
        for i in ids:
            c = counts[i]
            if c["mortal"] == 0 and c["immortal"] == 0:
                print(f"  WARN beast {i}: zero valid verdicts — classifying immortal "
                      f"by default (will resample if miscounted)", flush=True)
                continue
            if c["mortal"] > c["immortal"]:
                mortal.append(i)
        return mortal

    # ---- slaughter ---------------------------------------------------------

    def _slaughter(self, mortal_ids: List[int]):
        return post(f"{self.base}/api/slaughter", {"mortal": mortal_ids})

    @staticmethod
    def _flag_from(resp) -> Optional[str]:
        if resp is None:
            return None
        return find_flag(resp.text)

    @staticmethod
    def _miscount_from(resp) -> Optional[int]:
        if resp is None:
            return None
        import re
        m = re.search(r"(\d+)", resp.text)
        return int(m.group(1)) if m else None
