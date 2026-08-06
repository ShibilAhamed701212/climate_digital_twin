import urllib.request, json, time

start = time.time()
data = json.dumps({"model": "qwen3:4b", "prompt": "Hello", "stream": False}).encode()
try:
    r = urllib.request.urlopen(
        urllib.request.Request("http://localhost:11434/api/generate", data=data),
        timeout=180,
    )
    d = json.loads(r.read())
    elapsed = time.time() - start
    print(f"Direct call: {elapsed:.1f}s")
    print(f"Keys: {list(d.keys())}")
    resp = d.get("response", "MISSING")
    print(f"Response: {resp[:200]}")
except Exception as e:
    print(f"Direct call FAILED after {time.time() - start:.1f}s: {e}")
