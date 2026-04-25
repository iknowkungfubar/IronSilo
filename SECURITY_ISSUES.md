# IronSilo Security Issues - GitHub Issues Format

## P0 - Critical Priority

### Issue 1: [SECURITY] Fix timing attack vulnerability in API key authentication

**Labels:** `security`, `critical`, `bug`

**Description:**
The API key authentication in `security/middleware.py` uses simple string comparison (`!=`) which is vulnerable to timing attacks. An attacker can determine the API key character-by-character by measuring response times.

**Impact:**
- Authentication bypass
- Unauthorized access to all services

**Fix:**
Replace string comparison with `hmac.compare_digest()`:

```python
# File: security/middleware.py, line 110
# Change from:
if api_key != API_KEY:
# Change to:
if not hmac.compare_digest(api_key, API_KEY):
```

**Acceptance Criteria:**
- [ ] Import hmac module
- [ ] Replace all string comparisons with hmac.compare_digest
- [ ] Add unit test for timing-safe comparison

---

### Issue 2: [SECURITY] Fix SQL injection vulnerability in Genesys Memory API

**Labels:** `security`, `critical`, `bug`

**Description:**
The UPDATE endpoint in `genesys/app.py` constructs SQL queries using f-strings with user-controlled field names, enabling SQL injection.

**Impact:**
- Data exfiltration
- Data manipulation
- Potential RCE via PostgreSQL extensions

**Fix:**
Implement field whitelisting:

```python
# File: genesys/app.py, line 241
ALLOWED_UPDATE_FIELDS = {'memory_type', 'importance', 'tags', 'metadata'}

# Validate fields before building query
for k, v in kwargs.items():
    if v is not None and k in ALLOWED_UPDATE_FIELDS:
        # Use parameterized query
```

**Acceptance Criteria:**
- [ ] Implement field whitelist
- [ ] Validate all user inputs
- [ ] Add SQL injection test cases
- [ ] Remove f-string SQL construction

---

## P1 - High Priority

### Issue 3: [SECURITY] Restrict CORS origins in MCP framework

**Labels:** `security`, `high`, `bug`

**Description:**
MCP servers use `allow_origins=["*"]` with `allow_credentials=True`, enabling CSRF and data exfiltration attacks.

**Fix:**
```python
# File: mcp/framework.py, line 285
allow_origins=os.getenv("MCP_CORS_ORIGINS", "http://localhost:3000").split(",")
```

**Acceptance Criteria:**
- [ ] Remove wildcard CORS
- [ ] Add environment variable configuration
- [ ] Document CORS setup

---

### Issue 4: [SECURITY] Add rate limiting to MCP and Genesys endpoints

**Labels:** `security`, `high`, `enhancement`

**Description:**
MCP and Genesys API endpoints lack rate limiting, enabling DoS and brute-force attacks.

**Fix:**
- Apply security middleware to MCP FastAPI apps
- Apply security middleware to Genesys FastAPI app
- Configure per-service rate limits

**Acceptance Criteria:**
- [ ] Import and apply security middleware
- [ ] Test rate limiting works
- [ ] Add rate limit headers to responses

---

### Issue 5: [SECURITY] Sanitize health endpoint responses

**Labels:** `security`, `high`, `enhancement`

**Description:**
Health endpoints leak internal architecture details (backend type, database status, endpoint URLs).

**Fix:**
- Create minimal public health response
- Move detailed health to `/internal/health` (internal network only)
- Remove sensitive configuration from responses

**Acceptance Criteria:**
- [ ] Public health returns only status
- [ ] Internal health behind auth
- [ ] No endpoint URLs in responses

---

### Issue 6: [SECURITY] Pin Docker base image digests

**Labels:** `security`, `high`, `devops`

**Description:**
Dockerfiles use floating tags (`python:3.11-slim`) without digest pinning, vulnerable to supply chain attacks.

**Fix:**
```dockerfile
FROM python:3.11.8-slim-bookworm@sha256:abc123...
```

**Acceptance Criteria:**
- [ ] Pin all base images with SHA256 digest
- [ ] Document image update process
- [ ] Set up automated security scanning

---

### Issue 7: [SECURITY] Add authentication to Genesys Memory API

**Labels:** `security`, `high`, `enhancement`

**Description:**
Genesys API endpoints have no authentication when accessed directly (bypassing proxy).

**Fix:**
- Apply security middleware to genesys/app.py
- Reuse existing authentication infrastructure

**Acceptance Criteria:**
- [ ] All endpoints require authentication
- [ ] Health endpoint accessible without auth
- [ ] Document authentication setup

---

## P2 - Medium Priority

### Issue 8: [ENHANCEMENT] Reduce request size limit for chat endpoints

**Labels:** `security`, `medium`, `enhancement`

**Current:** 10MB limit  
**Recommended:** 1MB for chat, 10MB for file uploads

---

### Issue 9: [ENHANCEMENT] Add security headers middleware

**Labels:** `security`, `medium`, `enhancement`

**Headers to add:**
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Strict-Transport-Security
- Content-Security-Policy

---

### Issue 10: [ENHANCEMENT] Default to HTTPS for LLM endpoint

**Labels:** `security`, `medium`, `enhancement`

**Description:**
Default LLM endpoint uses HTTP. Should validate and prefer HTTPS.

---

### Issue 11: [SECURITY] Restrict extra fields pass-through in proxy

**Labels:** `security`, `medium`, `bug`

**Description:**
`extra="allow"` in Pydantic model permits arbitrary fields to upstream LLM.

**Fix:**
Whitelist allowed passthrough fields or remove feature.

---

### Issue 12: [ENHANCEMENT] Implement log level based on environment

**Labels:** `security`, `medium`, `enhancement`

**Description:**
Debug logging may expose sensitive data in production.

---

### Issue 13: [ENHANCEMENT] Remove request IDs from error responses

**Labels:** `security`, `medium`, `enhancement`

**Description:**
Error responses include internal request IDs that could aid attackers.

---

## P3 - Low Priority

### Issue 14: [ENHANCEMENT] Require password during setup

**Labels:** `security`, `low`, `enhancement`

---

### Issue 15: [ENHANCEMENT] Add TLS termination to docker-compose

**Labels:** `security`, `low`, `devops`

---

### Issue 16: [ENHANCEMENT] Encrypt key backup files

**Labels:** `security`, `low`, `enhancement`

---

### Issue 17: [ENHANCEMENT] Sanitize memory content for UI display

**Labels:** `security`, `low`, `enhancement`

---

## Implementation Checklist

### Phase 1 - Critical (Complete within 1 week)
- [ ] Issue 1: Fix timing attack in auth
- [ ] Issue 2: Fix SQL injection in Genesys

### Phase 2 - High (Complete within 2 weeks)
- [ ] Issue 3: Restrict CORS
- [ ] Issue 4: Add rate limiting to MCP/Genesys
- [ ] Issue 5: Sanitize health endpoints
- [ ] Issue 7: Add auth to Genesys

### Phase 3 - Medium (Complete within 1 month)
- [ ] Issue 8: Adjust request size limits
- [ ] Issue 9: Add security headers
- [ ] Issue 10: HTTPS defaults
- [ ] Issue 11: Restrict extra fields

### Phase 4 - Low (Backlog)
- [ ] Issues 12-17 as time permits
