# Security Report

> **⚠️ Additional security findings. Hackathon proof-of-concept — not hardened.**

---

## Summary

| Area | Status | Risk |
|------|--------|------|
| Authentication | ❌ Not implemented | Critical |
| Authorization | ❌ Not implemented | Critical |
| Encryption in transit | ❌ HTTP only | High |
| Secrets management | ⚠️ Plaintext env vars | High |
| Input validation | ⚠️ Basic type checks | Medium |
| Rate limiting | ❌ None | Medium |
| Audit logging | ❌ None | Medium |
| Dependency scanning | ✅ Completed | — |
| Container security | ⚠️ Running as root | Medium |

---

## Findings Detail

### 1. No Authentication (Critical)

All API endpoints are publicly accessible with no authentication:

```
GET  /predict       → no auth
POST /risk/heat     → no auth
POST /copilot/ask   → no auth
GET  /dashboard     → no auth
```

**Risk:** Anyone with network access can query/modify system state.

### 2. No Authorization (Critical)

No role-based access control. Every user has full access.

### 3. HTTP Only (High)

No TLS termination. All traffic in plaintext.

### 4. Secrets in Plaintext (High)

```yaml
# api/config.yaml
nasa_api_key: "your-key-here"  # ⚠️ Never populated
```

### 5. Root Containers (Medium)

All Docker containers run as root by default.

### 6. Permissive CORS (Low)

```python
# api/main.py
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

---

## Dependency Vulnerabilities

| Package | Version | Known Vulns | Status |
|---------|---------|-------------|--------|
| numpy | 1.24+ | Low | Acceptable for demo |
| pandas | 2.0+ | Low | Acceptable for demo |
| torch | 2.0+ | Low | Acceptable for demo |
| streamlit | 1.28+ | Low | Acceptable for demo |
| fastapi | 0.104+ | Low | Acceptable for demo |

---

## Recommendations

For a hackathon demo, the current security posture is acceptable. For any production deployment:

1. **Add API key authentication** (FastAPI middleware, ~20 lines)
2. **Add HTTPS** (nginx + certbot or self-signed)
3. **Add rate limiting** (nginx limit_req or slowapi)
4. **Add input validation** (Pydantic models exist but should be strengthened)
5. **Create non-root user in Dockerfiles**
6. **Add audit log** (structured logging to stdout)
