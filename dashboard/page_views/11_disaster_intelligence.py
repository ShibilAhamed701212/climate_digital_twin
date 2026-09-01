"""Page 11: Disaster Intelligence — observed inundation overlays."""  # noqa: N999

from __future__ import annotations

import json

import folium
import streamlit as st
from streamlit_folium import st_folium

from dashboard.config.config import DEFAULT_CENTER, DEFAULT_ZOOM, SAMPLE_LOCATIONS
from dashboard.services.api_client import DashboardAPI

_DEFAULT_AOI = {
    "type": "Polygon",
    "coordinates": [[[75.8, 12.8], [76.4, 12.8], [76.4, 13.2], [75.8, 13.2], [75.8, 12.8]]],
}


def render(api: DashboardAPI, filters: dict) -> None:
    st.header("Disaster Intelligence")
    st.caption(
        "Observed inundation from satellite thresholding intersected with OSM. "
        "Climate flood risk (rainfall scores) is a different product — see Climate Risk."
    )
    location_id = filters.get("location_id") or SAMPLE_LOCATIONS[0]["id"]
    with st.spinner("Loading disaster overlay…"):
        overlay = api.get_twin_overlay(location_id)
        events = api.list_disaster_events()
        models = api.list_disaster_models()

    with st.expander("Flood model status", expanded=True):
        st.caption(
            "Active mapper is configuration, not a published accuracy claim. "
            "Softmax margin is model confidence, not a calibrated flood probability."
        )
        st.write(
            {
                "Flood model": overlay.get("model_id") or models.get("active_flood"),
                "Sensor": overlay.get("sensor") or "n/a",
                "Polarization": overlay.get("polarization") or "n/a",
                "Runtime": overlay.get("runtime") or models.get("runtime"),
                "Device": overlay.get("device") or models.get("device"),
                "Checkpoint": (overlay.get("checkpoint_hash") or "")[:12] or "n/a",
                "Confidence": overlay.get("confidence_type"),
                "Fallback": overlay.get("fallback_used") or overlay.get("fallback_status"),
                "Fallback reason": overlay.get("fallback_reason") or "",
            }
        )
        for item in models.get("items") or []:
            st.caption(
                f"{item.get('id')}: enabled={item.get('enabled')} "
                f"runtime={item.get('runtime') or item.get('framework')} "
                f"{'(disabled: ' + str(item.get('reason') or '')[:80] + ')' if not item.get('enabled') and item.get('id') != 's1-threshold-v0' else ''}"
            )

    if overlay.get("processing_time"):
        st.caption(f"Processing status: completed · time_ms={overlay.get('processing_time')}")

    if not overlay.get("available") and not events:
        st.info(
            "Disaster Intelligence Engine has no assessment for this location "
            "(service down, or no job has completed)."
        )

    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    kpis = overlay.get("kpis") or {}
    with col_a:
        st.metric(
            "Flood area km²",
            kpis.get("flood_area_km2", "n/a") if overlay.get("available") else "n/a",
        )
    with col_b:
        st.metric(
            "Buildings in water",
            kpis.get("buildings_in_water", "n/a") if overlay.get("available") else "n/a",
        )
    with col_c:
        st.metric(
            "Hospitals in water",
            kpis.get("hospitals_in_water", "n/a") if overlay.get("available") else "n/a",
        )
    with col_d:
        pop = kpis.get("pop_exposed_est") if overlay.get("available") else None
        st.metric("Pop. exposed", pop if pop is not None else "unavailable")
    with col_e:
        conf = kpis.get("mean_confidence") if overlay.get("available") else None
        st.metric("Mask confidence", conf if conf is not None else "n/a")

    flags = overlay.get("quality_flags") or []
    if flags:
        st.caption("Quality flags: " + ", ".join(str(f) for f in flags))
    if overlay.get("authenticity"):
        st.caption(f"Authenticity badge: {overlay.get('authenticity')}")
    if overlay.get("model_cards"):
        st.caption("Models: " + ", ".join(f"{k}={v}" for k, v in overlay["model_cards"].items()))
    if overlay.get("confidence_mean") is not None:
        st.caption(
            "Mean confidence is boundary-agreement of the threshold mask, "
            f"not a calibrated probability ({overlay.get('confidence_mean')})."
        )

    st.markdown(
        "**Legend:** red = OSM feature in water · green = OSM feature dry · "
        "values are inundation ∩ OSM, not structural damage."
    )
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l1:
        show_buildings = st.checkbox("Buildings", value=True)
    with col_l2:
        show_roads = st.checkbox("Roads", value=True)
    with col_l3:
        show_amenities = st.checkbox("Amenities", value=False)

    fmap = folium.Map(location=DEFAULT_CENTER, zoom_start=DEFAULT_ZOOM)
    if overlay.get("available") and overlay.get("assessment_id"):
        aid = str(overlay["assessment_id"])
        if show_buildings:
            geo = api.get_disaster_geojson(aid, "buildings")
            if geo.get("features"):
                folium.GeoJson(
                    geo,
                    name="Buildings",
                    style_function=lambda feat: {
                        "color": "#c0392b"
                        if (feat.get("properties") or {}).get("in_water")
                        else "#27ae60",
                        "weight": 1,
                        "fillOpacity": 0.4,
                    },
                ).add_to(fmap)
        if show_roads:
            roads = api.get_disaster_geojson(aid, "roads")
            if roads.get("features"):
                folium.GeoJson(roads, name="Roads").add_to(fmap)
        if show_amenities:
            amenities = api.get_disaster_geojson(aid, "amenities")
            if amenities.get("features"):
                folium.GeoJson(amenities, name="Amenities").add_to(fmap)
    folium.LayerControl().add_to(fmap)
    st_folium(fmap, width=900, height=420)

    st.subheader("Run assessment")
    uploaded = st.file_uploader("GeoTIFF / COG", type=["tif", "tiff", "cog"])
    license_name = st.text_input("License", value="user-upload")
    if st.button("Ingest and run job") and uploaded is not None:
        try:
            created = api.create_disaster_event(
                {
                    "disaster_type": "flood",
                    "aoi": _DEFAULT_AOI,
                    "t_start": "2018-08-15T00:00:00Z",
                    "location_ids": [location_id],
                    "name": uploaded.name,
                }
            )
            api.upload_disaster_scene(
                created["event_id"], uploaded.getvalue(), uploaded.name, license_name
            )
            job = api.create_disaster_job(created["event_id"], twin_sync=True)
            st.session_state["die_job_id"] = job.get("job_id")
            st.success(f"Job queued: {job.get('job_id')}")
        except Exception as exc:
            st.error(f"Job failed to start: {exc}")

    job_id = st.session_state.get("die_job_id")
    if job_id:
        job = api.get_disaster_job(str(job_id))
        st.subheader("Job monitor")
        st.write(
            {
                "job_id": job_id,
                "status": job.get("status"),
                "stage": job.get("stage"),
                "progress_pct": job.get("progress_pct"),
                "error_code": job.get("error_code"),
                "error_message": job.get("error_message"),
            }
        )
        if job.get("status") == "failed":
            st.error(job.get("error_message") or "Job failed")
        bar = job.get("progress_pct")
        if isinstance(bar, (int, float)):
            st.progress(min(100, max(0, int(bar))) / 100.0)

    st.subheader("Jobs / events")
    jobs = api.list_disaster_jobs()
    if jobs:
        st.dataframe(jobs, use_container_width=True)
    if events:
        st.dataframe(events, use_container_width=True)
    else:
        st.write("No disaster events in the engine catalog.")

    if overlay.get("available") and overlay.get("assessment_id"):
        aid = str(overlay["assessment_id"])
        md = api.get_disaster_report(aid, location_id, "markdown")
        st.download_button("Download assessment markdown", md, file_name=f"{aid}.md")
        pdf = api.get_disaster_report(aid, location_id, "pdf")
        st.download_button("Download assessment PDF", pdf, file_name=f"{aid}.pdf")
        js = api.get_disaster_report(aid, location_id, "json")
        st.download_button("Download assessment JSON", js, file_name=f"{aid}.json")
        csvb = api.get_disaster_report(aid, location_id, "csv")
        st.download_button("Download assessment CSV", csvb, file_name=f"{aid}.csv")
        gj = api.get_disaster_report(aid, location_id, "geojson")
        st.download_button("Download assessment GeoJSON", gj, file_name=f"{aid}.geojson")
        geo_bytes = json.dumps(api.get_disaster_geojson(aid, "buildings")).encode()
        st.download_button(
            "Download buildings GeoJSON", geo_bytes, file_name=f"{aid}_buildings.geojson"
        )
        roads_bytes = json.dumps(api.get_disaster_geojson(aid, "roads")).encode()
        st.download_button("Download roads GeoJSON", roads_bytes, file_name=f"{aid}_roads.geojson")
        meta = json.dumps(overlay, indent=2).encode()
        st.download_button("Download overlay metadata", meta, file_name=f"{aid}_overlay.json")

    with st.expander("Raw overlay JSON"):
        st.code(json.dumps(overlay, indent=2))
