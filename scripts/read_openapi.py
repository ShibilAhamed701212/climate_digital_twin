import json

with open("scripts/openapi.json") as f:
    spec = json.load(f)

print(f"Title: {spec['info']['title']} v{spec['info']['version']}")
print(f"Paths: {len(spec['paths'])}")
for p, methods in sorted(spec["paths"].items()):
    print(f"  {p}: {list(methods.keys())}")
