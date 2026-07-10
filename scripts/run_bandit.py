import json
import os
import subprocess
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "bandit",
        "-r",
        "pipeline",
        "risk",
        "simulator",
        "knowledge",
        "copilot",
        "dashboard",
        "backend",
        "-f",
        "json",
    ],
    capture_output=True,
    text=True,
)
try:
    data = json.loads(result.stdout)
except json.JSONDecodeError:
    print("STDOUT:", result.stdout[:2000])
    print("STDERR:", result.stderr[:2000])
    sys.exit(1)

print(f"Bandit: {len(data['results'])} issues")
for r in data["results"]:
    print(
        f"  {r['test_id']} {r['filename']}:{r['line_number']} {r['issue_text']} ({r['severity']}/{r['confidence']})"
    )
