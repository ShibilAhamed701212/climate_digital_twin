from __future__ import annotations

from disaster_intelligence import __version__
from disaster_intelligence.application.container import get_container


def prometheus_text() -> str:
    c = get_container()
    totals_raw = c.metrics.get("disaster_jobs_total") or {}
    totals: dict[str, int] = totals_raw if isinstance(totals_raw, dict) else {}
    lines = [
        "# HELP disaster_jobs_total Disaster intelligence jobs by status",
        "# TYPE disaster_jobs_total counter",
    ]
    for status, value in totals.items():
        lines.append(f'disaster_jobs_total{{status="{status}"}} {int(value)}')
    inflight = int(c.metrics.get("disaster_inflight_jobs") or 0)
    lines.append("# HELP disaster_inflight_jobs Currently running jobs")
    lines.append("# TYPE disaster_inflight_jobs gauge")
    lines.append(f"disaster_inflight_jobs {inflight}")
    uploads = int(c.metrics.get("disaster_uploads_total") or 0)
    lines.append("# HELP disaster_uploads_total Accepted raster uploads")
    lines.append("# TYPE disaster_uploads_total counter")
    lines.append(f"disaster_uploads_total {uploads}")
    assessments = int(c.metrics.get("disaster_assessments_total") or 0)
    lines.append("# HELP disaster_assessments_total Completed assessments")
    lines.append("# TYPE disaster_assessments_total counter")
    lines.append(f"disaster_assessments_total {assessments}")
    disk_ok = int(c.metrics.get("disaster_disk_ok") or 1)
    lines.append("# HELP disaster_disk_ok Writable data directory")
    lines.append("# TYPE disaster_disk_ok gauge")
    lines.append(f"disaster_disk_ok {disk_ok}")
    lines.append(f"# VERSION {__version__}")
    return "\n".join(lines) + "\n"
