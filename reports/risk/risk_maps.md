# Risk Maps

> **⚠️ Maps generated from synthetic data.** No real hazard calibration.

---

## Map Generation

Risk maps are rendered as Folium choropleth overlays on OpenStreetMap tiles. Colors indicate risk category per district.

| Hazard | Data Source | Status |
|--------|-------------|--------|
| Heat risk | Synthetic scores per district | ✅ Demo quality |
| Flood risk | Synthetic scores per district | ✅ Demo quality |
| Drought risk | Synthetic scores per district | ✅ Demo quality |
| Composite risk | Weighted average of above | ✅ Demo quality |

---

## District Coverage

15 synthetic Karnataka districts (from config.yaml):
1. Kalaburagi
2. Vijayapura
3. Bidar
4. Raichur
5. Yadgir
6. Koppal
7. Ballari
8. Davanagere
9. Chitradurga
10. Tumakuru
11. Chikkaballapura
12. Kolar
13. Ramanagara
14. Mandya
15. Mysuru

---

## Color Scheme

| Risk Level | Hex | Description |
|------------|-----|-------------|
| Very Low | #00ff00 | 0–20 |
| Low | #ffff00 | 21–40 |
| Moderate | #ff8c00 | 41–60 |
| High | #ff0000 | 61–80 |
| Severe | #8b0000 | 81–100 |

---

## Limitations

1. **Synthetic coordinates.** District centroids are approximate.
2. **No admin boundaries.** Districts rendered as circle markers, not polygons.
3. **No spatial interpolation.** Individual district scores, no continuous surface.
4. **No real hazard layers.** No floodplains, fault lines, historical hazard zones.
