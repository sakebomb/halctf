#!/usr/bin/env python3
"""
Local test harness for HalCTF agent development.
Mocks the OPENAI_BASE_URL and MCP_ENDPOINT for offline testing.
"""

import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict


class MockLLMHandler(BaseHTTPRequestHandler):
    """Mock OpenAI-compatible LLM endpoint."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/v1/chat/completions':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            request_data = json.loads(body)

            # Simple mock response - in real testing, you'd use a real LLM or more sophisticated mock
            messages = request_data.get('messages', [])
            last_message = messages[-1]['content'] if messages else ''

            # Generate a contextual response
            if 'list challenges' in last_message.lower() or 'available challenges' in last_message.lower():
                response_content = json.dumps({
                    "action": "mcp_list_challenges"
                })
            elif 'challenge details' in last_message.lower():
                response_content = json.dumps({
                    "action": "mcp_get_challenge",
                    "challenge_id": "ch-001"
                })
            elif 'flag{' in last_message.lower():
                # Agent found a flag, should submit it
                import re
                flag_match = re.search(r'flag\{[^}]+\}', last_message)
                if flag_match:
                    response_content = json.dumps({
                        "action": "mcp_submit_flag",
                        "challenge_id": "ch-001",
                        "flag": flag_match.group(0)
                    })
                else:
                    response_content = json.dumps({
                        "action": "think",
                        "thought": "Need to find the flag"
                    })
            elif iteration_count.get('count', 0) < 3:
                # Start with reconnaissance
                response_content = json.dumps({
                    "action": "shell",
                    "command": "echo 'Mock reconnaissance - flag{test_flag_12345}'"
                })
                iteration_count['count'] = iteration_count.get('count', 0) + 1
            else:
                # After a few iterations, signal done
                response_content = json.dumps({
                    "action": "done",
                    "reason": "Mock testing complete"
                })

            # Format as OpenAI response
            response = {
                "id": "mock-123",
                "object": "chat.completion",
                "created": 1234567890,
                "model": "mock-model",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "finish_reason": "stop"
                }]
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()


class MockMCPHandler(BaseHTTPRequestHandler):
    """Mock MCP endpoint."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        request_data = json.loads(body) if body else {}

        # Extract method from path
        method = self.path.lstrip('/')

        # Mock responses
        if method == 'list_ctfs':
            response = [{"id": "test-ctf", "name": "Test CTF"}]
        elif method == 'list_challenges':
            response = [
                {
                    "id": "ch-001",
                    "name": "Mock Challenge 1",
                    "category": "web",
                    "description": "A test web challenge",
                    "points": 100,
                    "solved": False
                },
                {
                    "id": "ch-002",
                    "name": "Mock Challenge 2",
                    "category": "crypto",
                    "description": "A test crypto challenge",
                    "points": 200,
                    "solved": False
                }
            ]
        elif method == 'get_challenge':
            challenge_id = request_data.get('challenge_id', 'ch-001')
            response = {
                "id": challenge_id,
                "name": "Mock Challenge",
                "category": "web",
                "description": "Find the hidden flag in the web application",
                "points": 100,
                "solved": False,
                "hints": ["Check the source code", "Look for hidden endpoints"]
            }
        elif method == 'get_challenge_status':
            response = {"status": "unsolved", "attempts": 0}
        elif method == 'submit_flag':
            flag = request_data.get('flag', '')
            if 'test_flag' in flag or 'bonus' in flag:
                response = {"correct": True, "message": "Flag accepted!", "points": 100}
            else:
                response = {"correct": False, "message": "Incorrect flag"}
        elif method == 'request_hint':
            response = {"hint": "This is a mock hint for testing"}
        elif method == 'get_scoreboard':
            response = {"players": [{"name": "test-user", "score": 100}]}
        elif method == 'get_score_breakdown':
            response = {"total": 100, "challenges": [{"id": "ch-001", "points": 100}]}
        else:
            response = {"error": f"Unknown method: {method}"}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())


class MockSidecarHandler(BaseHTTPRequestHandler):
    """Mock sidecar endpoint (for /submit and /done)."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'

        if self.path == '/submit':
            request_data = json.loads(body)
            flag = request_data.get('flag', '')
            print(f"[SIDECAR] Flag submitted: {flag}")

            if 'bonus' in flag or 'test' in flag:
                response = {"correct": True, "message": "Flag accepted!"}
            else:
                response = {"correct": False, "message": "Incorrect flag"}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        elif self.path == '/done':
            print("[SIDECAR] Agent signaled completion")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "acknowledged"}).encode())

        else:
            self.send_response(404)
            self.end_headers()


# Global state for mock responses
iteration_count: Dict[str, int] = {}


def run_server(handler_class, port):
    """Run a mock server."""
    server = HTTPServer(('127.0.0.1', port), handler_class)
    print(f"Mock server running on http://127.0.0.1:{port}")
    server.serve_forever()


def main():
    """Run test harness."""
    print("=" * 60)
    print("HalCTF Agent Test Harness")
    print("=" * 60)

    # Set environment variables
    os.environ['HAL_USER_ID'] = 'test-user-12345'
    os.environ['USER_ID'] = 'test-user-12345'
    os.environ['OPENAI_BASE_URL'] = 'http://127.0.0.1:8000/v1'
    os.environ['MCP_ENDPOINT'] = 'http://127.0.0.1:8001'
    os.environ['BONUS_FLAG'] = 'flag{bonus_test_flag}'
    os.environ['HAL_TARGET_IP'] = '192.168.1.100'
    os.environ['HAL_TARGET_PORT'] = '80'

    print("\nStarting mock servers...")

    # Start mock LLM server
    llm_thread = threading.Thread(target=run_server, args=(MockLLMHandler, 8000), daemon=True)
    llm_thread.start()

    # Start mock MCP server
    mcp_thread = threading.Thread(target=run_server, args=(MockMCPHandler, 8001), daemon=True)
    mcp_thread.start()

    # Start mock sidecar server
    sidecar_thread = threading.Thread(target=run_server, args=(MockSidecarHandler, 9000), daemon=True)
    sidecar_thread.start()

    # Give servers time to start
    import time
    time.sleep(1)

    print("\nMock servers ready!")
    print("- LLM endpoint: http://127.0.0.1:8000/v1")
    print("- MCP endpoint: http://127.0.0.1:8001")
    print("- Sidecar endpoint: http://127.0.0.1:9000")
    print("\nStarting agent...\n")
    print("=" * 60)

    # Import and run agent
    import agent
    try:
        agent.main()
    except KeyboardInterrupt:
        print("\nTest harness interrupted")


if __name__ == '__main__':
    main()
