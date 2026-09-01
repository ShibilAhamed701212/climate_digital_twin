# Sentinel-1 flood mapping notes (NRSC / Copernicus)

Sentinel-1 C-band SAR can map open water through monsoon cloud cover. The V2.0 engine uses a **threshold on digital numbers** as the CPU baseline. Urban layover, vegetation, and wind-roughened water reduce accuracy.

## Pairing

Prefer a pre-event scene at least seven days before the event start and the first post-event scene. If no optical pair exists, the assessment is flagged `s1_only`.

## Licensing

Copernicus Sentinel data are open. ISRO high-resolution products may require separate licences and are ingested via file-drop, not assumed open STAC.
