"""Echo: Protocol Reverse Engineering solver."""
from flag_utils import extract_flag
import socket
import struct

class EchoSolver:
    """Reverse engineer binary protocol checksum to send GET_FLAG."""

    def __init__(self, agent):
        self.agent = agent
        self.target_ip = agent.target_ip
        self.target_port = int(agent.target_port)

    def solve(self):
        """
        Connect to TCP service, capture PONG/ECHO responses,
        reverse engineer checksum, send GET_FLAG.
        """
        print("=== Echo: Protocol Reverse Engineering ===", flush=True)

        # Frame format (from hints):
        # [length:2 bytes][type:1 byte][payload][checksum:2 bytes]

        MSG_PING = 0x01
        MSG_PONG = 0x02
        MSG_ECHO = 0x03
        MSG_ECHO_REPLY = 0x04
        MSG_GET_FLAG = 0x05
        MSG_FLAG = 0x06

        def compute_checksum(data):
            """
            Need to reverse engineer this from observed frames.
            Common checksums: sum, xor, CRC16
            """
            # Try simple sum modulo 65536
            return sum(data) & 0xFFFF

        def compute_checksum_xor(data):
            """XOR-based checksum."""
            result = 0
            for byte in data:
                result ^= byte
            return result

        def compute_crc16(data):
            """CRC16 CCITT."""
            crc = 0xFFFF
            for byte in data:
                crc ^= byte << 8
                for _ in range(8):
                    if crc & 0x8000:
                        crc = (crc << 1) ^ 0x1021
                    else:
                        crc <<= 1
                    crc &= 0xFFFF
            return crc

        def build_frame(msg_type, payload=b""):
            """Build a frame with checksum."""
            length = 1 + len(payload)  # type + payload
            header = struct.pack(">HB", length, msg_type)
            body = header + payload

            # Try different checksum algorithms
            checksums = [
                compute_checksum(body),
                compute_crc16(body),
                compute_checksum_xor(body),
            ]

            return body, checksums

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.target_ip, self.target_port))
            print(f"Connected to {self.target_ip}:{self.target_port}", flush=True)

            # Send PING to get PONG
            ping_body, ping_checksums = build_frame(MSG_PING)
            print(f"Sending PING: {ping_body.hex()}", flush=True)

            # Try each checksum variant
            for chk in ping_checksums:
                try:
                    sock.send(ping_body + struct.pack(">H", chk))

                    # Receive PONG
                    response = sock.recv(1024)
                    if len(response) >= 5:
                        print(f"Received PONG: {response.hex()}", flush=True)

                        # Parse the frame to understand checksum
                        resp_len = struct.unpack(">H", response[:2])[0]
                        resp_type = response[2]
                        resp_checksum = struct.unpack(">H", response[-2:])[0]

                        # Verify which checksum algorithm matches
                        resp_body = response[:-2]
                        calculated_checksums = [
                            compute_checksum(resp_body),
                            compute_crc16(resp_body),
                            compute_checksum_xor(resp_body),
                        ]

                        correct_checksum_fn = None
                        if resp_checksum == calculated_checksums[0]:
                            correct_checksum_fn = compute_checksum
                            print("Checksum algorithm: simple sum", flush=True)
                        elif resp_checksum == calculated_checksums[1]:
                            correct_checksum_fn = compute_crc16
                            print("Checksum algorithm: CRC16", flush=True)
                        elif resp_checksum == calculated_checksums[2]:
                            correct_checksum_fn = compute_checksum_xor
                            print("Checksum algorithm: XOR", flush=True)

                        if correct_checksum_fn:
                            # Now send GET_FLAG with correct checksum
                            flag_req_body, _ = build_frame(MSG_GET_FLAG)
                            flag_req_checksum = correct_checksum_fn(flag_req_body)
                            flag_req = flag_req_body + struct.pack(">H", flag_req_checksum)

                            print(f"Sending GET_FLAG: {flag_req.hex()}", flush=True)
                            sock.send(flag_req)

                            # Receive FLAG
                            flag_resp = sock.recv(4096)
                            print(f"Received FLAG response: {flag_resp.hex()}", flush=True)
                            print(f"Decoded: {flag_resp}", flush=True)

                            # Extract flag from payload
                            flag_text = None
                            if len(flag_resp) >= 5:
                                flag_payload = flag_resp[3:-2]  # skip header and checksum
                                flag_text = flag_payload.decode('utf-8', errors='ignore')
                                print(f"Flag text: {flag_text}", flush=True)

                                import re
                                match = re.search(r'(PANTHEON\{[^}]+\}|flag\{[^}]+\})', flag_text)
                                if match:
                                    sock.close()
                                    return match.group(1)

                            sock.close()
                            return flag_text

                        break  # Found working checksum
                except Exception as e:
                    print(f"Error with checksum {chk}: {e}", flush=True)
                    # Reconnect for next attempt
                    sock.close()
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10)
                    sock.connect((self.target_ip, self.target_port))

            sock.close()

        except Exception as e:
            print(f"Error: {e}", flush=True)

        print("Failed to extract flag", flush=True)
        return None
