"""Flag extraction utilities."""
import re

def extract_flag(text: str) -> str:
    """
    Extract CTF flag from text.

    Supports multiple flag formats:
    - HALCTF{...}
    - PANTHEON{...}
    - flag{...}

    Case insensitive matching.
    """
    if not text or "{" not in text or "}" not in text:
        return None

    # Try multiple patterns
    patterns = [
        r'HALCTF\{[^}]+\}',
        r'PANTHEON\{[^}]+\}',
        r'flag\{[^}]+\}',
        r'FLAG\{[^}]+\}',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)

    return None

def has_flag(text: str) -> bool:
    """Check if text contains a flag pattern."""
    return extract_flag(text) is not None
