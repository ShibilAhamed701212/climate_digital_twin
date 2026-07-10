"""Run vulture to find dead code."""

import subprocess
import sys

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "vulture",
        "pipeline/",
        "risk/",
        "simulator/",
        "knowledge/",
        "copilot/",
        "dashboard/",
        "backend/",
        "--min-confidence",
        "100",
    ],
    capture_output=True,
    text=True,
)
print(result.stdout[:3000] if result.stdout else "No dead code detected at 100% confidence")
