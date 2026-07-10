"""Health check script for all services."""

import sys
import urllib.error
import urllib.request

SERVICES = {
    "twin-state-mgr": "http://localhost:8001/health",
    "scenario-engine": "http://localhost:8002/health",
    "risk-engine": "http://localhost:8003/health",
    "rag-service": "http://localhost:8004/health",
    "copilot-agent": "http://localhost:8005/health",
    "forecast-engine": "http://localhost:8006/health",
    "fastapi-gateway": "http://localhost:8000/health",
    "streamlit-dashboard": "http://localhost:8501",
}

FAILED = 0
for name, url in SERVICES.items():
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        if resp.status < 400:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} (status {resp.status})")
            FAILED += 1
    except Exception as e:
        print(f"  ❌ {name} ({e})")
        FAILED += 1

if FAILED:
    print(f"\n{FAILED} service(s) unhealthy")
    sys.exit(1)
else:
    print("\nAll services healthy!")
