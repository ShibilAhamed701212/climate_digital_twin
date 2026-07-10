import json

with open("bandit_report.json") as f:
    d = json.load(f)
print(f"Bandit: {len(d['results'])} issues")
for r in d["results"]:
    sev = r.get("issue_severity", "?")
    conf = r.get("issue_confidence", "?")
    print(f"  {r['test_id']} {r['filename']}:{r['line_number']} {r['issue_text']} ({sev}/{conf})")
