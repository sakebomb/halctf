"""
Puzzle 2 — The Bag of Aeolus (Crypto / Scripting, 75 pts)

Keystream reuse: all 13 seals were XOR-encrypted with the SAME keystream from
byte 0. Twelve plaintexts (the winds) are given in the gazetteer, so any one
wind recovers keystream up to its length. The 13th seal ('the gift for the king
alone') has no gazetteer entry — XOR it against the recovered keystream to get
the flag. No verify endpoint; compute and submit directly.

Endpoints (on the challenge target):
  GET /api/bag        -> 13 hex-encoded seals (dict name->hex, or list)
  GET /api/gazetteer  -> 12 winds in plain words (dict name->text)
"""
from typing import Dict

from ._http import discover_base, find_flag, get
from ._llm import llm_extract_json


def _xor(a: bytes, b: bytes) -> bytes:
    """XOR up to the shorter length."""
    return bytes(x ^ y for x, y in zip(a, b))


def _as_name_map(obj) -> Dict[str, str]:
    """
    Normalize /api/bag and /api/gazetteer into a {name: value} dict.
    Accepts dict directly, or a list of {name/wind/label, value/seal/text/cipher}.
    """
    if isinstance(obj, dict):
        # Could be {name: value} already, or {"seals": {...}} / {"winds": {...}}.
        for k in ("seals", "winds", "bag", "gazetteer", "data", "items"):
            if k in obj and isinstance(obj[k], (dict, list)):
                return _as_name_map(obj[k])
        # Assume it's already name->value (values are str).
        if all(isinstance(v, str) for v in obj.values()):
            return {str(k): v for k, v in obj.items()}
        # name->{...} shape
        out = {}
        for k, v in obj.items():
            if isinstance(v, str):
                out[str(k)] = v
            elif isinstance(v, dict):
                val = (v.get("value") or v.get("seal") or v.get("sealed")
                       or v.get("cipher") or v.get("text") or v.get("hex")
                       or v.get("ciphertext"))
                if isinstance(val, str):
                    out[str(k)] = val
        return out
    if isinstance(obj, list):
        out = {}
        for it in obj:
            if not isinstance(it, dict):
                continue
            name = (it.get("name") or it.get("wind") or it.get("label")
                    or it.get("id") or it.get("title"))
            val = (it.get("value") or it.get("seal") or it.get("sealed")
                   or it.get("cipher") or it.get("text") or it.get("hex")
                   or it.get("ciphertext") or it.get("plaintext"))
            if name is not None and isinstance(val, str):
                out[str(name)] = val
        return out
    return {}


class AeolusSolver:
    def __init__(self, agent):
        self.agent = agent

    def solve(self) -> bool:
        print("=== Aeolus Solver (XOR keystream reuse) ===", flush=True)
        base = discover_base(self.agent.target_ip, self.agent.target_port)
        if not base:
            return False

        bag_resp = get(f"{base}/api/bag")
        gaz_resp = get(f"{base}/api/gazetteer")
        if bag_resp is None or gaz_resp is None:
            print("Could not fetch bag/gazetteer", flush=True)
            return False

        try:
            seals = _as_name_map(bag_resp.json())
            gazetteer = _as_name_map(gaz_resp.json())
        except Exception as e:
            print(f"Failed to parse bag/gazetteer JSON: {e}", flush=True)
            return False

        # LLM fallback if deterministic parsing returned empty
        if not seals:
            print("[LLM] deterministic seal parsing failed, asking LLM...", flush=True)
            result = llm_extract_json(
                "Extract seal names and their hex-encoded values as a dict {name: hex_string}",
                bag_resp.text,
                {"seal_name": "hex_value"}
            )
            if result and isinstance(result, dict):
                seals = result
                print(f"[LLM] extracted {len(seals)} seals", flush=True)

        if not gazetteer:
            print("[LLM] deterministic gazetteer parsing failed, asking LLM...", flush=True)
            result = llm_extract_json(
                "Extract wind names and their plaintext descriptions as a dict {name: text}",
                gaz_resp.text,
                {"wind_name": "plaintext"}
            )
            if result and isinstance(result, dict):
                gazetteer = result
                print(f"[LLM] extracted {len(gazetteer)} winds", flush=True)

        print(f"Seals: {list(seals)}", flush=True)
        print(f"Gazetteer winds: {list(gazetteer)}", flush=True)

        # Identify the gift seal: the one seal whose name has NO gazetteer entry.
        gift_names = [n for n in seals if n not in gazetteer]
        # Fallback: match the hint's label text.
        if not gift_names:
            gift_names = [n for n in seals if "gift" in n.lower() or "king" in n.lower()]
        if not gift_names:
            print("Could not identify the gift seal", flush=True)
            return False
        gift_name = gift_names[0]
        print(f"Gift seal: {gift_name!r}", flush=True)

        try:
            gift_ct = bytes.fromhex(seals[gift_name].strip())
        except ValueError as e:
            print(f"Gift seal is not valid hex: {e}", flush=True)
            return False

        # Recover keystream from any wind long enough, prefer longest first so we
        # cover the whole gift ciphertext. Any single wind that reaches the gift
        # length suffices, but combining lets us fill gaps if one is short.
        keystream = bytearray(len(gift_ct))
        covered = [False] * len(gift_ct)
        winds_by_len = sorted(
            (n for n in gazetteer if n in seals),
            key=lambda n: len(gazetteer[n]), reverse=True,
        )
        for name in winds_by_len:
            try:
                ct = bytes.fromhex(seals[name].strip())
            except ValueError:
                continue
            pt = gazetteer[name].encode()
            ks = _xor(ct, pt)  # keystream up to len(min(ct, pt))
            for i in range(min(len(ks), len(gift_ct))):
                if not covered[i]:
                    keystream[i] = ks[i]
                    covered[i] = True

        if not all(covered):
            missing = covered.index(False)
            print(f"Keystream only recovered up to byte {missing} of {len(gift_ct)}; "
                  f"winds too short. Trying partial decode.", flush=True)

        flag_bytes = _xor(bytes(keystream), gift_ct)
        try:
            flag = flag_bytes.decode()
        except UnicodeDecodeError:
            flag = flag_bytes.decode("latin-1", errors="replace")
        print(f"Decrypted gift: {flag!r}", flush=True)

        found = find_flag(flag) or (flag if flag.startswith("HALCTF{") else None)
        if not found:
            # Last resort: the gift may itself be a bare flag missing prefix noise.
            print("Decrypted string is not a clean HALCTF{...}; submitting as-is.", flush=True)
            found = flag.strip()
        return self.agent.submit_flag(found, self.agent.challenge_id)
