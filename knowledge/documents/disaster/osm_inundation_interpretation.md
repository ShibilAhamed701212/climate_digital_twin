# OSM inundation intersection — interpretation

OpenStreetMap footprints and amenities are used to count buildings, roads, hospitals, and schools that intersect a water mask.

- `in_water` does **not** mean the building is structurally destroyed.
- Damage class is `unknown` when inundated and `none` otherwise (xBD CNN is disabled in V2.0).
- Hospital amenity completeness varies by district (`OSM_INCOMPLETE` flag).
- ODbL attribution is required when publishing derived OSM extracts.
