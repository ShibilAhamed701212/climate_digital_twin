"""Validate DIE OpenAPI contains frozen disaster routes. No network required."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from disaster_intelligence.api.main import app  # noqa: E402

REQUIRED = {
    "/health",
    "/disaster/events",
    "/disaster/jobs",
    "/disaster/models",
    "/disaster/integrations",
    "/disaster/assessments/{assessment_id}/report",
}


def main() -> int:
    spec = app.openapi()
    paths = set(spec.get("paths") or {})
    missing = sorted(REQUIRED - paths)
    if missing:
        raise SystemExit(f"OpenAPI missing paths: {missing}")
    report = spec["paths"]["/disaster/assessments/{assessment_id}/report"]["get"]
    params = report.get("parameters") or []
    fmt = next((p for p in params if p.get("name") == "fmt"), None)
    if fmt is None:
        raise SystemExit("report fmt parameter missing")
    print("openapi_ok", len(paths), "paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
