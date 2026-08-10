"""
Puzzle 6 — The Bow of Odysseus (Networking / Protocol, 150 pts)

Raw TCP socket with binary frame protocol. 108 suitors, 12 axe heads. The spec
is attached to the challenge (runtime-fetched). Use the "sign" from Tiresias
(EURYKLEIA) for authentication.

Endpoints: Raw TCP socket at HAL_TARGET_IP:HAL_TARGET_PORT (port 9099).
The protocol spec (bow_protocol.md) is fetched at runtime via MCP get_challenge
or from common HTTP paths.
"""
import os
import socket
import struct
from typing import Optional, Tuple

from ._http import find_flag, get
from ._llm import llm_parse_protocol_spec


class BowSolver:
    def __init__(self, agent):
        self.agent = agent
        self.target_ip = os.environ.get("HAL_TARGET_IP", "")
        self.target_port = int(os.environ.get("HAL_TARGET_PORT", "9099"))
        self.sign = "EURYKLEIA"  # From Tiresias challenge

    def solve(self) -> bool:
        print("=== Bow of Odysseus Solver (binary protocol, raw socket) ===", flush=True)

        if not self.target_ip:
            print("No target IP available", flush=True)
            return False

        # Step 1: Fetch the protocol spec
        spec = self._fetch_spec()
        if not spec:
            print("Could not fetch bow_protocol.md spec — cannot proceed without protocol details", flush=True)
            return False

        print(f"Fetched protocol spec ({len(spec)} bytes)", flush=True)
        print(f"[spec] preview:\n{spec[:800]}", flush=True)

        # Step 2: Use LLM to parse spec and generate implementation
        print("[LLM] asking LLM to parse protocol spec and generate implementation...", flush=True)
        generated_code = llm_parse_protocol_spec(spec, self.sign)

        if generated_code:
            print(f"[LLM] generated {len(generated_code)} bytes of code", flush=True)
            # Execute LLM-generated protocol implementation
            flag = self._execute_generated_protocol(generated_code)
            if flag:
                return self.agent.submit_flag(flag, self.agent.challenge_id)
        else:
            print("[LLM] spec parsing failed, falling back to generic protocol", flush=True)

        # Fallback: generic protocol (if LLM fails)
        flag = self._execute_protocol(spec)
        if flag:
            return self.agent.submit_flag(flag, self.agent.challenge_id)

        return False

    def _fetch_spec(self) -> Optional[str]:
        """
        Fetch bow_protocol.md from available sources:
        1. MCP get_challenge (may include attachments)
        2. Common HTTP paths on target or sidecar
        """
        print(f"[spec] fetching bow_protocol.md", flush=True)

        # Try MCP get_challenge
        try:
            from mcp_client import get_challenge_details
            details = get_challenge_details(self.agent.ctf_name, self.agent.challenge_name)
            if details and isinstance(details, dict):
                print(f"[spec] MCP returned keys: {list(details.keys())}", flush=True)

                # Check for attachments/files in response
                for key in ("attachments", "files", "spec", "protocol", "notes"):
                    if key in details:
                        content = details[key]

                        # Handle string content directly
                        if isinstance(content, str) and len(content) > 100:
                            print(f"[spec] found via MCP key='{key}' (string)", flush=True)
                            return content

                        # Handle list of attachment objects
                        if isinstance(content, list) and len(content) > 0:
                            print(f"[spec] found attachments list with {len(content)} items", flush=True)
                            for attachment in content:
                                if isinstance(attachment, dict):
                                    # Try to find the spec file
                                    name = attachment.get("name", "") or attachment.get("filename", "")
                                    if "bow" in name.lower() or "protocol" in name.lower() or "spec" in name.lower():
                                        # Extract content from various possible fields
                                        spec_content = (attachment.get("content") or
                                                       attachment.get("data") or
                                                       attachment.get("text") or
                                                       attachment.get("body"))
                                        if spec_content and len(str(spec_content)) > 100:
                                            print(f"[spec] found spec in attachment '{name}'", flush=True)
                                            return str(spec_content)

                            # If no matching name, try first attachment
                            if len(content) > 0 and isinstance(content[0], dict):
                                first = content[0]
                                spec_content = (first.get("content") or first.get("data") or
                                               first.get("text") or first.get("body"))
                                if spec_content and len(str(spec_content)) > 100:
                                    print(f"[spec] using first attachment (no name match)", flush=True)
                                    return str(spec_content)
        except Exception as e:
            print(f"[spec] MCP fetch failed: {e}", flush=True)
            import traceback
            traceback.print_exc()

        # Try common HTTP paths
        # Target might serve it on port 8000/80/8080/actual port, sidecar might have /attachment
        paths = [
            # Try target on common HTTP ports
            f"http://{self.target_ip}:8000/bow_protocol.md",
            f"http://{self.target_ip}:8000/protocol.md",
            f"http://{self.target_ip}:8000/spec.md",
            f"http://{self.target_ip}:80/bow_protocol.md",
            f"http://{self.target_ip}:8080/bow_protocol.md",
            # Try target on actual challenge port (might serve spec via HTTP before switching to binary)
            f"http://{self.target_ip}:{self.target_port}/bow_protocol.md",
            f"http://{self.target_ip}:{self.target_port}/protocol.md",
            f"http://{self.target_ip}:{self.target_port}/spec.md",
            # Try sidecar paths
            "http://127.0.0.1:9000/attachment/bow_protocol.md",
            "http://127.0.0.1:9000/files/bow_protocol.md",
            "http://127.0.0.1:9000/challenge/attachment",
        ]

        for url in paths:
            resp = get(url, log=False)
            if resp and resp.status_code == 200 and len(resp.text) > 100:
                print(f"[spec] found at {url}", flush=True)
                return resp.text
            if resp:
                print(f"[spec] {url} -> {resp.status_code}", flush=True)

        return None

    def _execute_protocol(self, spec: str) -> Optional[str]:
        """
        Parse the spec and execute the binary protocol.

        Expected from spec:
        - Frame format (header + payload)
        - Authentication using sign "EURYKLEIA"
        - 12 shots through axe heads
        - Response contains flag
        """
        print(f"[protocol] analyzing spec...", flush=True)

        # Log the spec for debugging
        print(f"[protocol] spec preview:\n{spec[:500]}", flush=True)

        # Generic binary protocol client
        # The spec will likely describe:
        # - A header (e.g., magic bytes, length, command)
        # - Authentication frame with sign
        # - Shot frames (12 times)
        # - Final response with flag

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((self.target_ip, self.target_port))
            print(f"[protocol] connected to {self.target_ip}:{self.target_port}", flush=True)

            # Read any greeting/banner
            try:
                banner = sock.recv(1024)
                if banner:
                    print(f"[protocol] banner: {banner[:200]}", flush=True)
            except socket.timeout:
                pass

            # Without the actual spec, we'll need to implement a generic approach
            # Parse spec for frame format hints
            frame_format = self._parse_frame_format(spec)

            # Send authentication with sign
            if "auth" in frame_format or "sign" in spec.lower():
                auth_frame = self._build_auth_frame(frame_format)
                sock.sendall(auth_frame)
                print(f"[protocol] sent auth frame with sign={self.sign!r}", flush=True)

                resp = sock.recv(4096)
                print(f"[protocol] auth response: {resp[:200]}", flush=True)

            # Send 12 shot frames
            for shot in range(1, 13):
                shot_frame = self._build_shot_frame(shot, frame_format)
                sock.sendall(shot_frame)
                print(f"[protocol] shot {shot}/12", flush=True)

                resp = sock.recv(4096)
                if resp:
                    print(f"[protocol] shot {shot} response: {resp[:100]}", flush=True)

            # Read final response (should contain flag)
            final = sock.recv(4096)
            print(f"[protocol] final response: {final}", flush=True)

            sock.close()

            # Extract flag from response
            flag = find_flag(final.decode(errors='ignore'))
            if flag:
                print(f"[protocol] extracted flag: {flag}", flush=True)
                return flag

            # Flag might be in earlier responses too
            return None

        except Exception as e:
            print(f"[protocol] execution failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None

    def _parse_frame_format(self, spec: str) -> dict:
        """
        Parse the spec to understand frame format.
        Returns hints about protocol structure.
        """
        hints = {
            "has_magic": "magic" in spec.lower() or "0x" in spec,
            "has_length": "length" in spec.lower(),
            "has_command": "command" in spec.lower() or "opcode" in spec.lower(),
            "uses_sign": "sign" in spec.lower() or "EURYKLEIA" in spec,
            "shots": "12" in spec or "twelve" in spec.lower(),
        }
        print(f"[protocol] parsed hints: {hints}", flush=True)
        return hints

    def _build_auth_frame(self, hints: dict) -> bytes:
        """
        Build authentication frame.
        Common format: [magic][length][command][payload]
        Payload contains sign "EURYKLEIA"
        """
        # Generic frame: 4-byte magic, 2-byte length, 1-byte command, payload
        magic = b'\x42\x4F\x57\x00'  # "BOW\0" as placeholder
        command = b'\x01'  # Auth command
        payload = self.sign.encode('utf-8')
        length = struct.pack('>H', len(payload))

        return magic + length + command + payload

    def _build_shot_frame(self, shot_num: int, hints: dict) -> bytes:
        """
        Build shot frame for axe head number.
        """
        magic = b'\x42\x4F\x57\x00'  # "BOW\0"
        command = b'\x02'  # Shot command
        payload = struct.pack('>H', shot_num)  # Shot number
        length = struct.pack('>H', len(payload))

        return magic + length + command + payload

    def _execute_generated_protocol(self, code: str) -> Optional[str]:
        """
        Execute LLM-generated protocol implementation.
        The code should define execute_protocol(target_ip, target_port, sign).
        """
        print("[LLM] executing generated protocol implementation...", flush=True)

        try:
            # Create namespace with required imports
            namespace = {
                'socket': socket,
                'struct': struct,
                'find_flag': find_flag,
            }

            # Execute the generated code to define the function
            exec(code, namespace)

            # Call the generated function
            if 'execute_protocol' not in namespace:
                print("[LLM] generated code missing execute_protocol function", flush=True)
                return None

            execute_protocol = namespace['execute_protocol']
            result = execute_protocol(self.target_ip, self.target_port, self.sign)

            if isinstance(result, str):
                print(f"[LLM] protocol returned: {result[:200]}", flush=True)
                return result

            return None

        except Exception as e:
            print(f"[LLM] execution failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None
