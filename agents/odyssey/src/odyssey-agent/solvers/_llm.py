"""
LLM-assisted solving utilities.

Provides adaptive fallbacks when deterministic parsing fails. Uses the
HAL_AGENT_MODEL via OPENAI_BASE_URL endpoint (127.0.0.1:9000/llm).
"""
import json
import os
import re
from typing import Any, Dict, List, Optional

import requests


def _get_llm_endpoint() -> Optional[str]:
    """Get LLM endpoint from environment."""
    base = os.environ.get("OPENAI_BASE_URL", "")
    if not base:
        return None
    # Ensure it has /v1/chat/completions
    if not base.endswith("/"):
        base += "/"
    if "v1/chat/completions" in base:
        return base.rstrip("/")
    return base.rstrip("/") + "/v1/chat/completions"


def llm_call(prompt: str, temperature: float = 0.0, max_tokens: int = 1000) -> Optional[str]:
    """
    Make a raw LLM call and return text response.
    Returns None if LLM unavailable or call fails.
    """
    endpoint = _get_llm_endpoint()
    if not endpoint:
        return None

    model = os.environ.get("HAL_AGENT_MODEL", "google/gemma-4-26b-a4b-it-maas")

    try:
        resp = requests.post(
            endpoint,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=30.0,
        )
        if resp.status_code != 200:
            print(f"[LLM] call failed: {resp.status_code}", flush=True)
            return None

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip()

    except Exception as e:
        print(f"[LLM] call exception: {e}", flush=True)
        return None


def llm_extract_json(prompt: str, data: str, schema_hint: Optional[Dict] = None) -> Optional[Any]:
    """
    Ask LLM to extract structured data from text/JSON.
    Returns parsed JSON object or None.

    Example:
      llm_extract_json(
        "Extract crew names from this shore register response",
        api_response_text
      )
    """
    schema_text = ""
    if schema_hint:
        schema_text = f"\n\nExpected output schema: {json.dumps(schema_hint)}"

    full_prompt = f"""{prompt}{schema_text}

Input data:
{data[:2000]}

Extract the relevant data and return ONLY valid JSON, nothing else."""

    response = llm_call(full_prompt, temperature=0.0, max_tokens=500)
    if not response:
        return None

    # Extract JSON from response (handle markdown code blocks)
    json_text = response
    if "```json" in response:
        match = re.search(r"```json\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            json_text = match.group(1)
    elif "```" in response:
        match = re.search(r"```\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            json_text = match.group(1)

    try:
        return json.loads(json_text.strip())
    except json.JSONDecodeError as e:
        print(f"[LLM] JSON parse failed: {e}. Response: {response[:200]}", flush=True)
        return None


def llm_extract_field(prompt: str, json_obj: Dict) -> Optional[Any]:
    """
    Ask LLM to extract a specific field from a JSON object when field name is unknown.

    Example:
      llm_extract_field(
        "Find the field containing the flag fragment (a partial HALCTF{...} string)",
        {"tide": 1, "spew": "HALCTF{abc", "message": "..."}
      )
      # Returns: "HALCTF{abc"
    """
    json_str = json.dumps(json_obj, indent=2)
    full_prompt = f"""{prompt}

JSON object:
{json_str}

Return ONLY the extracted value, nothing else."""

    response = llm_call(full_prompt, temperature=0.0, max_tokens=200)
    if not response:
        return None

    # Clean up response
    cleaned = response.strip().strip('"').strip("'")
    return cleaned if cleaned else None


def llm_parse_protocol_spec(spec_text: str, sign: str) -> Optional[str]:
    """
    Parse a binary protocol spec and generate Python implementation code.

    Returns executable Python code as a string, or None if parsing fails.
    """
    prompt = f"""You are a binary protocol implementation expert. Parse this protocol specification and generate a complete Python function to implement it.

Protocol Specification:
{spec_text[:4000]}

Requirements:
1. The function should connect to a TCP socket (target_ip, target_port)
2. Implement authentication using the sign: "{sign}"
3. Send all required frames per the spec (e.g., 12 shots through axe heads)
4. Return the flag extracted from the response
5. Use Python's struct and socket modules
6. Include error handling and logging

Generate ONLY the Python function code (def execute_protocol(target_ip, target_port, sign):), nothing else. No markdown, no explanations, just valid Python code."""

    response = llm_call(prompt, temperature=0.0, max_tokens=2000)
    if not response:
        return None

    # Extract code from response
    code = response
    if "```python" in response:
        match = re.search(r"```python\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            code = match.group(1)
    elif "```" in response:
        match = re.search(r"```\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            code = match.group(1)

    # Verify it has the expected function
    if "def execute_protocol" not in code:
        print(f"[LLM] Generated code missing execute_protocol function", flush=True)
        return None

    return code.strip()


def llm_suggest_field_name(api_response: str, target_description: str) -> Optional[str]:
    """
    When API rejects our field name (422), ask LLM what the correct field name is.

    Example:
      llm_suggest_field_name(
        '{"error": "unknown field \'url\'"}',
        "the URL parameter for SSRF chart endpoint"
      )
      # Returns: "target"
    """
    prompt = f"""An API rejected our request. We need to find the correct field name.

What we're trying to send: {target_description}

API response:
{api_response[:500]}

What is the correct field name to use? Return ONLY the field name, nothing else."""

    response = llm_call(prompt, temperature=0.0, max_tokens=50)
    if not response:
        return None

    # Clean and validate
    field_name = response.strip().strip('"').strip("'").strip()
    # Field names are typically alphanumeric + underscores
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field_name):
        return field_name

    return None
