"""Test RAG search with various queries."""

import json
import urllib.request

for q in ["India", "monsoon", "Karnataka", "rainfall", "temperature", "climate"]:
    req_data = json.dumps({"query": q, "k": 5}).encode()
    req = urllib.request.Request(
        "http://localhost:8004/search",
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=10)
        data = json.loads(r.read())
        count = data.get("total_results", 0)
        print(f"{q}: {count} results")
        if data.get("results"):
            for res in data["results"][:2]:
                text_preview = res.get("text", "")[:60]
                print(f"  - {res.get('id', '?')}: {res.get('score', 0):.3f} ...{text_preview}...")
    except Exception as e:
        print(f"{q}: error {e}")
