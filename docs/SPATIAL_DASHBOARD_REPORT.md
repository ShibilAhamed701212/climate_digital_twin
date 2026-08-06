# Spatial Dashboard Report

The Spatial Grid page now loads the full Karnataka monthly dataset instead of the 25-cell validation subset.

Implemented controls and layers:

- Year, month, and hourly time-step controls.
- Manual animation frame advance.
- Temperature, rainfall, humidity, pressure, wind, and ET0 estimate layers.
- Native-grid interpolation display.
- District overlay using configured real Karnataka locations.
- Folium zoom, pan, hover tooltips, selection, and layer control.
- Selected-cell inspection and regional statistics.
- Forecast and hazard overlays call the live backend only; unavailable backend values are not fabricated.

Dashboard image rebuilt and the 651-cell loader verified in-container.
