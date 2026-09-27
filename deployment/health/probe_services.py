"""
RAMP Automated Service Probe
SIH26080 | Phase 17 — Production Deployment & Operational Reliability
"""

import sys
import urllib.request
import json

ENDPOINTS = [
    "/health/live",
    "/health/ready",
    "/health/data",
    "/health/models",
    "/health/inference",
    "/health/operations",
    "/health/overall",
]

def probe(base_url="http://localhost:8000"):
    print(f"=== Probing RAMP Endpoints at {base_url} ===")
    all_ok = True
    for ep in ENDPOINTS:
        url = base_url + ep
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RAMP-Probe/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                print(f"[HTTP {resp.status}] {ep} -> {data.get('status', 'OK')}")
        except Exception as e:
            print(f"[FAILED] {ep} -> {e}")
            all_ok = False
    return 0 if all_ok else 1

if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    sys.exit(probe(base))
