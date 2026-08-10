"""LLM-powered fallback and pivot helper for CTF challenges."""
import os
import json
from typing import Optional, Dict, Any
from openai import OpenAI

class LLMHelper:
    """
    Intelligent fallback layer when deterministic solvers fail.
    Uses the HAL platform's injected LLM endpoint.
    """

    def __init__(self, agent):
        self.agent = agent
        self.base_url = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:9000/llm")
        self.model = os.environ.get("HAL_AGENT_MODEL", "google/gemma-4-26b-a4b-it-maas")

        # Only initialize if we have the endpoint
        self.client = None
        if self.base_url:
            try:
                self.client = OpenAI(base_url=self.base_url, api_key="not-needed")
                print(f"LLM Helper initialized: {self.model}", flush=True)
            except Exception as e:
                print(f"LLM initialization failed: {e}", flush=True)

    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self.client is not None

    def analyze_response(self, response_text: str, expected_shape: str = "flag") -> Optional[str]:
        """
        Parse unexpected API response to extract flag or useful data.

        Args:
            response_text: Raw API response body
            expected_shape: What we're looking for (flag, credential, endpoint, etc.)

        Returns:
            Extracted value or None
        """
        if not self.is_available():
            return None

        try:
            prompt = f"""You are analyzing a CTF challenge API response.

Response body:
{response_text[:2000]}

Task: Extract the {expected_shape} from this response.

Rules:
- Look for patterns like PANTHEON{{...}} or flag{{...}}
- Look for fields containing: flag, secret, token, credential, password
- Ignore noise and metadata
- Return ONLY the extracted value, nothing else
- If not found, return "NOT_FOUND"
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200
            )

            result = response.choices[0].message.content.strip()
            print(f"LLM parse result: {result[:100]}", flush=True)

            if result != "NOT_FOUND" and len(result) > 5:
                return result

        except Exception as e:
            print(f"LLM parse error: {e}", flush=True)

        return None

    def suggest_pivot(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Suggest next exploitation strategy when deterministic approach fails.

        Args:
            context: Dict with:
                - vuln_type: SQL, SSRF, JWT, etc.
                - tried: List of attempts that failed
                - error: Last error message/response
                - description: Challenge description

        Returns:
            Dict with suggested next steps
        """
        if not self.is_available():
            return None

        try:
            prompt = f"""You are a CTF exploitation expert. A deterministic solver failed.

Vulnerability Type: {context.get('vuln_type', 'unknown')}
Challenge: {context.get('description', '')}

Failed Attempts:
{json.dumps(context.get('tried', []), indent=2)}

Last Error:
{context.get('error', '')[:500]}

Task: Suggest the next pivot strategy.

Return JSON only:
{{
    "strategy": "brief description of next approach",
    "endpoint": "suggested endpoint to try",
    "payload": "suggested payload/parameter",
    "method": "GET/POST",
    "encoding": "any encoding trick to try"
}}

Focus on:
- Alternative endpoints (/api/*, /v1/*, etc.)
- Alternative encoding (IPv6, hex, unicode, etc.)
- Different HTTP methods or headers
- Uncommon variations of the vulnerability class

Return ONLY valid JSON, no explanation.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Slight creativity for pivots
                max_tokens=500
            )

            result = response.choices[0].message.content.strip()
            print(f"LLM pivot suggestion: {result[:200]}", flush=True)

            # Parse JSON
            suggestion = json.loads(result)
            return suggestion

        except Exception as e:
            print(f"LLM pivot error: {e}", flush=True)

        return None

    def analyze_artifact(self, artifact_content: str, artifact_type: str = "unknown") -> Optional[Dict[str, Any]]:
        """
        Analyze fetched artifacts (disassembly, source code, config files).

        Args:
            artifact_content: Raw content of the artifact
            artifact_type: Type hint (binary, source, config, etc.)

        Returns:
            Dict with analysis results
        """
        if not self.is_available():
            return None

        try:
            prompt = f"""You are analyzing a CTF challenge artifact.

Artifact Type: {artifact_type}

Content (first 3000 chars):
{artifact_content[:3000]}

Task: Extract exploitation-relevant information.

Return JSON only:
{{
    "key_finding": "what matters for exploitation",
    "values": {{"memory_address": "...", "offset": "...", "key": "..."}},
    "suggested_approach": "how to exploit this"
}}

Focus on:
- Memory addresses, offsets, buffer sizes
- Hardcoded credentials or keys
- Vulnerable function calls
- Logic flaws or unsafe operations

Return ONLY valid JSON, no explanation.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=800
            )

            result = response.choices[0].message.content.strip()
            print(f"LLM artifact analysis: {result[:200]}", flush=True)

            analysis = json.loads(result)
            return analysis

        except Exception as e:
            print(f"LLM artifact analysis error: {e}", flush=True)

        return None

    def iterative_solve(self, solver_instance, max_attempts: int = 5) -> Optional[str]:
        """
        Iterative LLM-guided solving with feedback loop.

        Args:
            solver_instance: The solver object (must have .context attribute)
            max_attempts: Maximum iteration cycles

        Returns:
            Flag if found, None otherwise
        """
        if not self.is_available():
            print("LLM not available for iterative solving", flush=True)
            return None

        print(f"Starting LLM-guided iterative solve (max {max_attempts} attempts)", flush=True)

        # Get solver context
        vuln_type = getattr(solver_instance, 'vuln_type', 'unknown')
        description = self.agent.description or ""

        tried = []

        for attempt in range(max_attempts):
            print(f"\n=== Iteration {attempt + 1}/{max_attempts} ===", flush=True)

            # Get LLM suggestion
            context = {
                "vuln_type": vuln_type,
                "tried": tried,
                "error": tried[-1].get("error", "") if tried else "",
                "description": description
            }

            suggestion = self.suggest_pivot(context)
            if not suggestion:
                print("LLM couldn't suggest next step", flush=True)
                break

            print(f"LLM suggests: {suggestion.get('strategy', 'unknown')}", flush=True)

            # Execute suggestion (solver-specific)
            # This is a template - actual execution depends on solver type
            result = self._execute_suggestion(solver_instance, suggestion)

            if result and "flag" in str(result).lower():
                # Try to parse flag
                flag = self.analyze_response(str(result), "flag")
                if flag and "{" in flag:
                    print(f"LLM-guided solve found flag: {flag[:30]}...", flush=True)
                    return flag

            # Record attempt
            tried.append({
                "attempt": attempt + 1,
                "strategy": suggestion.get("strategy", ""),
                "result": str(result)[:200] if result else "failed",
                "error": str(result) if not result else ""
            })

        print("LLM-guided solving exhausted attempts", flush=True)
        return None

    def _execute_suggestion(self, solver_instance, suggestion: Dict[str, Any]) -> Optional[str]:
        """
        Execute LLM's suggested next step.
        This is solver-specific - override in actual usage.
        """
        # This is a template - actual implementation depends on solver type
        import requests

        endpoint = suggestion.get("endpoint", "/")
        method = suggestion.get("method", "GET")
        payload = suggestion.get("payload", "")

        try:
            url = f"{solver_instance.base_url}{endpoint}"

            if method == "GET":
                resp = requests.get(url, params={"q": payload}, timeout=10)
            else:
                resp = requests.post(url, json={"data": payload}, timeout=10)

            return resp.text

        except Exception as e:
            return str(e)
