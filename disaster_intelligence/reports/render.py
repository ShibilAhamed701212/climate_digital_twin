from __future__ import annotations

import csv
import io
import json

from disaster_intelligence.domain.entities import Assessment


def render_markdown(location: str, assessment: Assessment) -> str:
    kpis = assessment.kpis
    flags = ", ".join(assessment.quality_flags) or "none"
    pop = kpis.get("pop_exposed_est")
    pop_line = "unavailable (no census join)" if pop is None else str(pop)
    lines = [
        f"# Disaster Assessment Report — {location}",
        "",
        f"**Assessment ID:** {assessment.assessment_id}",
        f"**Event ID:** {assessment.event_id}",
        f"**Version:** {assessment.version}",
        f"**Type:** {assessment.disaster_type}",
        f"**Authenticity:** {assessment.authenticity}",
        f"**Quality flags:** {flags}",
        f"**Models:** {assessment.model_cards}",
        f"**Created:** {assessment.created_at}",
        "",
        "## Provenance",
        "",
        f"- Source API: `/disaster/assessments/{assessment.assessment_id}`",
        f"- Overlay: `/disaster/twin/{location}`",
        f"- Parent assessment: {assessment.parent_assessment_id or 'none'}",
        "- Method: threshold flood segmentation ∩ OSM (not structural damage)",
        "",
        "## Observed impact (inundation ∩ OSM)",
        "",
        "Building classes are inundation proxies, not xBD structural damage.",
        "",
        f"- Flood area (km²): {kpis.get('flood_area_km2')}",
        f"- Buildings in water: {kpis.get('buildings_in_water')}",
        f"- Roads in water (km, heuristic): {kpis.get('roads_in_water_km')}",
        f"- Hospitals in water: {kpis.get('hospitals_in_water')}",
        f"- Schools in water: {kpis.get('schools_in_water')}",
        f"- Population exposed (est.): {pop_line}",
        f"- Mean confidence: {kpis.get('mean_confidence')}",
        "",
        "## Disclaimer",
        "",
        "This product is not a dispatch system of record. Values originate from",
        "threshold flood segmentation and OSM intersection only.",
        "",
    ]
    return "\n".join(lines)


def render_json(location: str, assessment: Assessment) -> str:
    payload = assessment.to_dict()
    payload["location"] = location
    payload["provenance"] = {
        "href_assessment": f"/disaster/assessments/{assessment.assessment_id}",
        "href_overlay": f"/disaster/twin/{location}",
        "method": "threshold_flood_osm_intersect",
    }
    return json.dumps(payload, indent=2)


def render_csv(assessment: Assessment) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["key", "value"])
    writer.writerow(["assessment_id", assessment.assessment_id])
    writer.writerow(["event_id", assessment.event_id])
    writer.writerow(["authenticity", assessment.authenticity])
    writer.writerow(["quality_flags", "|".join(assessment.quality_flags)])
    for key, value in sorted(assessment.kpis.items()):
        writer.writerow([key, value])
    return buf.getvalue()


def render_geojson(location: str, assessment: Assessment) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "assessment_id": assessment.assessment_id,
                    "location": location,
                    "authenticity": assessment.authenticity,
                    "quality_flags": assessment.quality_flags,
                    "model_cards": assessment.model_cards,
                    **assessment.kpis,
                    "href": f"/disaster/assessments/{assessment.assessment_id}",
                },
                "geometry": None,
            }
        ],
    }


def render_pdf(markdown: str) -> bytes:
    """Minimal single-page PDF wrapping UTF-8 text (no third-party PDF stack)."""
    text = markdown.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = text.split("\n")[:60]
    y = 780
    content_ops = ["BT", "/F1 9 Tf"]
    for line in lines:
        safe = line[:110] or " "
        content_ops.append(f"1 0 0 1 40 {y} Tm ({safe}) Tj")
        y -= 12
        if y < 40:
            break
    content_ops.append("ET")
    stream = "\n".join(content_ops).encode("latin-1", errors="replace")
    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    )
    objects.append(
        b"4 0 obj << /Length "
        + str(len(stream)).encode()
        + b" >> stream\n"
        + stream
        + b"\nendstream endobj\n"
    )
    objects.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj\n")
    xref_positions = []
    out = bytearray(b"%PDF-1.1\n")
    for obj in objects:
        xref_positions.append(len(out))
        out += obj
    xref_start = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for pos in xref_positions:
        out += f"{pos:010d} 00000 n \n".encode()
    out += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
    ).encode()
    return bytes(out)
