#!/usr/bin/env python3
"""
Monitor HALCTF Run Status
Checks status of both v1 and v2 agent runs
"""
import requests
import json
import sys
from datetime import datetime

# Run IDs
V1_RUN_ID = "e227b8a8a79c182cc16eb03123400596"
V2_RUN_ID = "996b75d539b0b91a7ccdfd5a8b7bbb9b"

def check_run_status(session, run_id, version):
    """Check status of a specific run"""
    url = f"https://halctf.aivillage.org/run/{run_id}"

    try:
        resp = session.get(url, timeout=10)
        print(f"\n{'='*60}")
        print(f"{version} Run Status - {run_id}")
        print(f"{'='*60}")
        print(f"HTTP Status: {resp.status_code}")

        if resp.status_code == 200:
            # Try to extract status from HTML
            html = resp.text

            # Look for common status indicators
            if "pending" in html.lower():
                print("Status: PENDING")
            elif "running" in html.lower():
                print("Status: RUNNING")
            elif "completed" in html.lower():
                print("Status: COMPLETED")
            elif "failed" in html.lower():
                print("Status: FAILED")
            else:
                print("Status: UNKNOWN")

            # Look for queue position
            if "queue" in html.lower():
                print("⚠ In queue")

            # Look for flag submission
            if "HALCTF{" in html:
                import re
                flags = re.findall(r'HALCTF\{[^}]+\}', html)
                if flags:
                    print(f"🚩 Flags found: {flags}")

            # Save full response for manual inspection
            output_file = f"run_{version}_status.html"
            with open(output_file, 'w') as f:
                f.write(html)
            print(f"Full response saved to: {output_file}")
        else:
            print(f"❌ Request failed: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")

    except Exception as e:
        print(f"❌ Error checking {version}: {e}")

def main():
    """Main monitoring function"""
    print(f"HALCTF Run Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if we have a session cookie file
    cookie_file = ".halctf_cookies.json"

    session = requests.Session()

    # Try to load cookies if available
    try:
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        print("✓ Loaded session cookies")
    except FileNotFoundError:
        print("⚠ No session cookies found - responses may require authentication")
        print(f"To save cookies, export them from Brave and save to: {cookie_file}")

    # Check both runs
    check_run_status(session, V1_RUN_ID, "V1")
    check_run_status(session, V2_RUN_ID, "V2")

    print(f"\n{'='*60}")
    print("Next Steps:")
    print("1. Open Brave and navigate to:")
    print(f"   V1: https://halctf.aivillage.org/run/{V1_RUN_ID}")
    print(f"   V2: https://halctf.aivillage.org/run/{V2_RUN_ID}")
    print("2. Check status manually in browser")
    print("3. If you need automated monitoring, export cookies from Brave")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
