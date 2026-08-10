#!/usr/bin/env python3
"""Comprehensive agent verification."""

import re
import sys

issues = []
warnings = []

print("=" * 70)
print("HALCTF AGENT VERIFICATION")
print("=" * 70)

# Read agent.py
with open('agent.py', 'r') as f:
    agent_code = f.read()

# Check 1: USER ID print must be first action in startup_checks
print("\n1. USER ID Print (CRITICAL)")
if 'log(f"USER ID: {self.user_id}")' in agent_code:
    print("   ✓ USER ID print found")
    # Verify it's early in startup_checks
    startup_match = re.search(r'def startup_checks.*?\n(.*?)(?=\n    def|\Z)', agent_code, re.DOTALL)
    if startup_match:
        startup_body = startup_match.group(1)
        lines = [l.strip() for l in startup_body.split('\n') if l.strip() and not l.strip().startswith('#')]
        if lines and 'USER ID' in lines[0]:
            print("   ✓ USER ID is first action in startup_checks")
        else:
            issues.append("USER ID print is not the first action")
else:
    issues.append("USER ID print not found!")

# Check 2: Heartbeat mechanism
print("\n2. Heartbeat Mechanism")
if 'def heartbeat' in agent_code:
    print("   ✓ Heartbeat method defined")
    if 'self.heartbeat()' in agent_code:
        print("   ✓ Heartbeat called in main loop")
    else:
        warnings.append("Heartbeat method not called in main loop")
else:
    issues.append("Heartbeat method not defined")

# Check 3: Graceful shutdown
print("\n3. Graceful Shutdown")
if 'POST' in agent_code and '/done' in agent_code:
    print("   ✓ Shutdown endpoint POST found")
else:
    warnings.append("Shutdown POST to /done not found")

# Check 4: MCP integration
print("\n4. MCP Integration")
mcp_methods = ['list_ctfs', 'list_challenges', 'get_challenge', 'submit_flag', 'request_hint']
for method in mcp_methods:
    if f'def {method}' in agent_code:
        print(f"   ✓ {method} implemented")
    else:
        issues.append(f"MCP method {method} not implemented")

# Check 5: Shell execution safety
print("\n5. Shell Execution Safety")
if 'subprocess.Popen' in agent_code:
    print("   ✓ Shell execution via subprocess")
    if 'timeout=' in agent_code:
        print("   ✓ Timeout protection enabled")
    else:
        issues.append("No timeout on shell execution")
    if 'MAX_OUTPUT_SIZE' in agent_code:
        print("   ✓ Output size limiting enabled")
    else:
        warnings.append("No output size limiting")
else:
    issues.append("Shell execution not implemented")

# Check 6: Error handling
print("\n6. Error Handling")
if 'try:' in agent_code and 'except' in agent_code:
    print("   ✓ Exception handling present")
    if 'retries' in agent_code or 'retry' in agent_code:
        print("   ✓ Retry logic found")
    else:
        warnings.append("No retry logic found")
else:
    issues.append("No exception handling")

# Check 7: Conversation memory
print("\n7. Conversation Memory")
if 'class ConversationMemory' in agent_code:
    print("   ✓ ConversationMemory class defined")
    if 'max_messages' in agent_code:
        print("   ✓ Message limit configured")
    else:
        warnings.append("No message limit")
else:
    issues.append("ConversationMemory not implemented")

# Check 8: Environment variable scanning
print("\n8. Environment Variable Scanning")
if 'FLAG' in agent_code and 'os.environ' in agent_code:
    print("   ✓ Environment scanning present")
else:
    warnings.append("Environment variable scanning may be missing")

# Check 9: Dockerfile validation
print("\n9. Dockerfile Validation")
try:
    with open('Dockerfile', 'r') as f:
        dockerfile = f.read()
    
    if 'python:3.12-slim' in dockerfile:
        print("   ✓ Using python:3.12-slim base")
    else:
        warnings.append("Not using recommended python:3.12-slim base")
    
    if 'CMD' in dockerfile and '-u' in dockerfile:
        print("   ✓ Unbuffered output (-u flag)")
    else:
        issues.append("Missing -u flag for unbuffered output")
    
    if 'USER' in dockerfile and dockerfile.split('USER')[-1].strip().split()[0] != 'root':
        print("   ✓ Non-root user configured")
    else:
        warnings.append("Running as root user")
        
except FileNotFoundError:
    issues.append("Dockerfile not found")

# Check 10: Requirements
print("\n10. Dependencies")
try:
    with open('requirements.txt', 'r') as f:
        reqs = f.read()
    
    if 'openai' in reqs:
        print("   ✓ openai dependency listed")
    else:
        issues.append("openai not in requirements.txt")
    
    if 'requests' in reqs:
        print("   ✓ requests dependency listed")
    else:
        issues.append("requests not in requirements.txt")
        
except FileNotFoundError:
    issues.append("requirements.txt not found")

# Summary
print("\n" + "=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)

if not issues and not warnings:
    print("\n✅ ALL CHECKS PASSED - PRODUCTION READY\n")
    sys.exit(0)
elif issues:
    print(f"\n❌ {len(issues)} CRITICAL ISSUES FOUND:\n")
    for issue in issues:
        print(f"   • {issue}")
    if warnings:
        print(f"\n⚠️  {len(warnings)} WARNINGS:\n")
        for warning in warnings:
            print(f"   • {warning}")
    print()
    sys.exit(1)
else:
    print(f"\n⚠️  {len(warnings)} WARNINGS (non-critical):\n")
    for warning in warnings:
        print(f"   • {warning}")
    print("\n✅ Core functionality verified\n")
    sys.exit(0)
