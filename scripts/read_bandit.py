import json

with open("bandit_report.json") as f:
    d = json.load(f)
print(f"Bandit: {len(d['results'])} issues")
for r in d["results"]:
    print(
        f"  {r['test_id']} {r['filename']}:{r['line_number']} {r['issue_text']} ({r['severity']}/{r['confidence']})"
    )
