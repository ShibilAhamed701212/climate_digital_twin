"""Test RAG search with correct keys."""

import json
import urllib.request

req_data = json.dumps({"query": "Karnataka", "top_k": 5}).encode()
req = urllib.request.Request(
    "http://localhost:8004/search",
    data=req_data,
    headers={"Content-Type": "application/json"},
    method="POST",
)
r = urllib.request.urlopen(req, timeout=30)
data = json.loads(r.read())
print(f"Total results: {data.get('total_results')}")
for res in data.get("results", []):
    cid = res.get("chunk_id", "?")
    score = res.get("score", 0)
    title = res.get("title", "")
    content = res.get("content", "")[:80]
    print(f"  chunk_id={cid} score={score:.3f}")
    print(f"  title={title} content_preview={content}...")
