# River gauges above the reservoirs, on their DEM catchments

Generated 2026-11-23 23:09 UTC by `pipeline/upstream_catchments.py`. Observed records only; no model output is used and nothing is fitted.

The two gauges measure the river above each lake, independently of the reservoir balance from which the operator computes daily inflow. Neither SIBH nor ANA's inventory gives a drainage area, so `pipeline/delineate.py` derives them from the Copernicus DEM (3 arc-seconds), snapping each gauge to the nearest stream draining at least 20 km2. The other snap rule (largest flow accumulation within 540 m) is shown as the area's sensitivity.

## The catchments

| Gauge | River (ANA inventory) | DEM area (km2) | Other snap rule (km2) | Snap distance (m) | Share of the dam catchment | Cells outside the dam catchment | Outlet to the OSM river line (m) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3E-122 1430 | Rio da Cachoeira | 295.5 | 301.5 | 20 | 74% | 0 | 13 |
| 3E-121 1397 | Rio Atibainha | 128.4 | 136.6 | 48 | 41% | 0 | 21 |

Nesting holds when no cell lies outside the dam catchment. The outlet distance is from the snapped DEM cell (90 m) to the mapped river line; under about 100 m means the gauge sits on the river the inventory names.

## 3E-122 Rio da Cachoeira above Cachoeira: runoff against rain, by year

Rain on the gauge catchment from 10 gauges within 20 km of its centroid (audited, inverse-distance weighted). Runoff depth = discharge x 86.4 / 295.5 km2. The dam columns use the operator's daily inflow over the 397.0 km2 dam catchment and forcing.py's rain, on the days both exist. Years with at least 300 days.

| Year | Days | Rain (mm) | Gauge runoff (mm) | Gauge runoff ratio | Dam days | Dam rain (mm) | Operator inflow (mm) | Dam runoff ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | 363 | 2323 | 501 | 0.22 | 363 | 1912 | 408 | 0.21 |
| 2023 | 365 | 2217 | 650 | 0.29 | 365 | 1907 | 396 | 0.21 |
| 2025 | 360 | 1125 | 359 | 0.32 | 360 | 1116 | 178 | 0.16 |
| 2026 | 326 | 1837 | 589 | 0.32 | 326 | 1788 | 449 | 0.25 |

## 3E-121 Rio Atibainha above Atibainha: runoff against rain, by year

Rain on the gauge catchment from 24 gauges within 20 km of its centroid (audited, inverse-distance weighted). Runoff depth = discharge x 86.4 / 128.4 km2. The dam columns use the operator's daily inflow over the 313.2 km2 dam catchment and forcing.py's rain, on the days both exist. Years with at least 300 days.

| Year | Days | Rain (mm) | Gauge runoff (mm) | Gauge runoff ratio | Dam days | Dam rain (mm) | Operator inflow (mm) | Dam runoff ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 365 | 1240 | 463 | 0.37 | 365 | 1358 | 312 | 0.23 |
| 2020 | 366 | 1206 | 491 | 0.41 | 366 | 1153 | 268 | 0.23 |
| 2021 | 364 | 1172 | 507 | 0.43 | 364 | 1147 | 269 | 0.23 |
| 2022 | 362 | 1549 | 506 | 0.33 | 362 | 1523 | 374 | 0.25 |
| 2023 | 364 | 1698 | 687 | 0.40 | 364 | 1632 | 470 | 0.29 |
| 2024 | 366 | 1357 | 626 | 0.46 | 366 | 1308 | 315 | 0.24 |
| 2025 | 364 | 1137 | 554 | 0.49 | 364 | 1168 | 278 | 0.24 |
| 2026 | 325 | 1710 | 716 | 0.42 | 325 | 1707 | 489 | 0.29 |

## Limits

- The areas come from a 90 m surface model (canopy included) and carry the snap uncertainty in the first table; runoff depth scales inversely with them.
- Gauge discharge is SIBH's unconsolidated telemetric record, from a rating curve the open data do not let us check (see `sibh_flow_report.md`). 3E-121's rating changed in 2023 and again in 2024: from 2024 the same stage gives 23-41% more discharge, so its 2024 onward runoff is not comparable with earlier years.
- Rain is the same inverse-distance interpolation of point gauges used for the forcing; it is derived, not measured over the area.
- Calendar years; storage carry-over between years is ignored.
