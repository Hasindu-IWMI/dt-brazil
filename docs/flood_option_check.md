# Flood option C: data check for a hydraulic run through Atibaia town

Checked 16 November 2026, after `docs/model_design_hydraulic_run1.md` was
drafted. Observed records and image catalogues only. No model was run, and
nothing here is a design.

## Summary

- **The river does overflow in Atibaia town, often.** SP Águas' telemetric
  gauge 3E-063 (Rio Atibaia, Av. São João, 110 m from ANA's telemetric code
  62669900) has official levels: attention 239.9 cm, alert 261 cm, emergency
  279.9 cm and **overflow ("extravasamento") 301 cm**. Since Sentinel-1
  began (October 2014) the daily mean stage has been above 301 cm on 275 days,
  in 30 separate floods that reached 330 cm or more. The highest was 417 cm
  (8 June 2016). What exactly overflows at 301 cm, and where, is SP Águas'
  definition and should be confirmed with them.
- **25 of those 30 floods have at least one Sentinel-1 image taken while the
  river was above the overflow level** (section 2). In the best cases the
  river was 0.5–0.75 m above it at the moment of the pass.
- **The flow at which it overflows is about 20–24 m³/s.** ANA's and SIBH's
  ratings agree on this (median 23.3 and 23.9 m³/s on the 141 days above
  301 cm that both cover, 2010–2022).
- **ANA's daily record at Atibaia (62670000) holds spurious high days.** In
  three of the largest "floods" since 2014, ANA's value is three to four
  times what both telemetric stations recorded on the same day (table
  below). Otherwise the two records agree: the median ratio is 0.97–1.11 in
  every flow class below 30 m³/s.
- **Sentinel-1 covers this area well.** There are Stripmap images (about
  9 m resolution, against about 20 m for the standard wide-swath mode) from
  two orbits, plus wide-swath passes, from 2015 to now. Coverage was best with
  two satellites (to December 2021, and again with Sentinel-1C and 1D in
  2026). Sentinel-2 was mostly clouded at the floods checked. Two scenes may
  be usable: 7 January 2019 (3% cloud on the tile; river at about 300 cm,
  near the overflow level) and 16 January 2021 (25% cloud; 346 cm). Whether
  the town itself was clear needs a look at the scenes.

## 1. ANA's spurious days

Daily discharge (m³/s). 3E-063 is at the same site as ANA's gauge; 62671200
is 4 km downstream, above the Salto Grande small hydro plant.

| Day | ANA 62670000 | SIBH 3E-063 (stage, cm) | SIBH 62671200 |
| --- | --- | --- | --- |
| 2021-01-13 | 89.0 | 20 (318) | 23 |
| 2021-01-14 | 104.4 | 30 (356) | 37 |
| 2021-01-15 | 109.8 | 30 (356) | 41 |
| 2021-01-16 | 106.4 | 26 (346) | 39 |
| 2021-01-17 | 90.8 | 24 (338) | 34 |
| 2021-01-18 | 22.7 | 20 (326) | 27 |
| 2023-02-04 | 103.1 | 38 (379) | – |
| 2019-01-05 | 84.7 | 24 (331) | not credible (see below) |
| 2019-01-06 | 82.3 | 22 (318) | not credible |

- ANA's own record contradicts itself: 89 m³/s on 13 January 2021 and 23 m³/s
  on 18 January, with the river higher on the 18th (326 cm against 318 cm).
- In 2021 ANA's values would mean that about three-quarters of the 130 mm of
  rain measured nearby (CEMADEN, Bom Jesus dos Perdões, 11–17 January) ran
  off the 351 km² between the upstream gauges and Atibaia within the week,
  followed by an overnight drop from 91 to 23 m³/s. The telemetric record
  implies about a quarter ran off and a gradual recession, which is
  plausible.
- The highest stage at 3E-063 since 2014 was on 8 June 2016 (417 cm daily
  mean), when ANA recorded 79 m³/s and SIBH 54 m³/s. ANA's ranking of
  floods does not follow the stage at its own site.
- Yearly volume, ANA over SIBH: 1.00–1.09 in 2015–2017 and 2020, 1.16 in
  2019, **1.25 in 2021 and 1.24 in 2022**. The 2022 excess has no obvious
  spurious peak and is not explained here.

**Consequence beyond option C:** the runoff investigation
(`docs/runoff_shift_investigation.md`, frozen) used ANA 62670000 for the
351 km² area between the dams and Atibaia, and found it yielding 16–39% more
than the climate estimate since 2017. Spurious high days in ANA's record
would produce part of that excess. This is not a re-run of that analysis; it
is a data fault to record.

The station above the Salto Grande plant (62671200) is no help on
discharge: on 5 January 2019 its rating gives 623 m³/s for a level only
15 cm above that of 15 January 2021 (41 m³/s). Its **level** record may still
be usable.

## 2. Floods since Sentinel-1 began, and the images taken during them

Floods are ranked by daily mean stage at 3E-063 (SIBH daily means; a flood
counts once if peaks are less than 10 days apart). That uses no rating at
all. For each flood, Sentinel-1 GRD scenes from 2 days before to 6 days after
the peak were listed, and the hourly stage at the time of each pass was read
from 3E-063. The table gives the pass with the highest stage. Extra-wide
(40 m) scenes are left out, since they are too coarse for this river.
Times are UTC; local time is three hours earlier, so 21:4x UTC is early
evening and 08:3x UTC is before dawn.

| Flood peak day | Peak daily mean (cm) | Best pass (UTC) | Mode, polarisation | Stage at the pass (cm) | Above overflow |
| --- | --- | --- | --- | --- | --- |
| 2015-02-19 | 339 | 2015-02-17 21:35 | Stripmap, HH/HV | 311 | +10 |
| 2016-01-17 | 384 | 2016-01-19 21:35 | Stripmap, HH/HV | 341 | +40 |
| 2016-02-22 | 352 | 2016-02-25 08:30 | Wide swath, VV/VH | 339 | +38 |
| 2016-03-12 | 358 | 2016-03-12 21:43 | Stripmap, VV/VH | 350 | +49 |
| 2016-06-08 | 417 | 2016-06-11 21:35 | Stripmap, HH/HV | 328 | +27 |
| 2017-01-13 | 337 | 2017-01-12 21:43 | Stripmap, VV/VH | 343 | +42 |
| 2017-01-23 | 395 | 2017-01-24 21:43 | Stripmap, VV/VH | 361 | +60 |
| 2018-02-01 | 341 | 2018-02-01 21:35 | Stripmap, HH/HV | 340 | +39 |
| 2018-03-04 | 332 | 2018-03-04 08:30 | Wide swath, VV/VH | 333 | +32 |
| 2019-03-04 | 346 | 2019-03-04 21:35 | Stripmap, HH/HV | 345 | +44 |
| 2020-02-27 | 359 | 2020-02-27 21:35 | Stripmap, HH/HV | 360 | +59 |
| 2021-01-15 | 357 | 2021-01-15 21:43 | Stripmap, VV/VH | 351 | +50 |
| 2021-03-09 | 335 | 2021-03-10 21:44 | Stripmap, VV/VH | 323 | +22 |
| 2022-02-02 | 369 | 2022-02-04 21:36 | Stripmap, HH/HV | 330 | +29 |
| 2022-12-30 | 361 | 2022-12-30 21:44 | Stripmap, VV/VH | 360 | +59 |
| 2023-02-04 | 379 | 2023-02-04 21:44 | Stripmap, VV/VH | 377 | +76 |
| 2023-10-10 | 347 | 2023-10-10 08:31 | Wide swath, VV/VH | 348 | +47 |
| 2024-12-29 | 385 | 2024-12-27 08:31 | Wide swath, VV/VH | 326 | +25 |
| 2025-02-06 | 334 | 2025-02-05 21:44 | Stripmap, VV/VH | 334 | +33 |
| 2026-02-01 | 334 | 2026-02-01 21:35 | Stripmap, HH/HV | 331 | +30 |
| 2026-02-11 | 386 | 2026-02-12 21:44 | Stripmap, VV/VH | 377 | +76 |
| 2026-02-28 | 372 | 2026-02-26 08:30 | Wide swath, VV/VH | 324 | +23 |
| 2026-03-14 | 358 | 2026-03-14 21:43 | Stripmap, VV/VH | 356 | +55 |
| 2026-09-14 | 377 | 2026-09-13 08:30 | Wide swath, VV/VH | 377 | +76 |
| 2026-10-27 | 352 | 2026-10-25 08:30 | Wide swath, VV/VH | 308 | +7 |

No pass above the overflow level: 2016-01-28 (335 cm), 2019-01-05 (332),
2020-02-06 (355; the nearest pass found 292 cm), 2023-12-01 (336; no scene in
the window) and 2024-02-25 (350).

- Most floods were imaged more than once above the overflow level, often
  in both modes within 12 hours (for example 26–28 February 2020, 15–17
  January 2021, 14–16 March 2026). That gives repeat looks at the same water.
- The flood of record in this period (8 June 2016, 417 cm) was imaged only
  three days later, at 328 cm.
- The January 2017 floods match the press report of the river overflowing
  in Atibaia from 17 January 2017. The stage was 342 cm at the 18 January
  pass.
- The catalogue lists scenes; no image has been downloaded or looked at. The
  scenes from ascending passes (21:xx UTC) are Stripmap in two alternating
  polarisation pairs, so a time series of one orbit and polarisation is
  available for a dry-weather reference.

## 3. What a flood run here would have to settle first

- **The reach.** From 3E-063 (discharge in, measured) to the level station
  above the Salto Grande plant, about 4 km downstream (level out, as a check
  or as the downstream boundary). Caetetuba, one of the neighbourhoods named
  in flood reports, lies between the two, about 3 km below the gauge. The
  plant's weir probably controls water levels upstream at some flows, so the
  downstream boundary matters.
- **Terrain.** ANADEM is still the minimum. Urban flood extents on a 30 m
  grid are coarse; buildings are not represented in a bare-earth model.
- **Discharge at high flows.** The SIBH rating is the one consistent with
  stage and rain. Above about 30 m³/s the two ratings part (median ANA/SIBH
  1.32), and SIBH's rating above that range has not been checked. Its
  published curves (`/v1/key_curves/of_station_prefixes`) should be.
- **Gauge datum.** The overflow level gives a tie between the gauge's zero
  and the terrain: the bank at the gauge should sit near 301 cm on the
  gauge scale. That is a check on ANADEM there, as well as a datum.
- **Flood extent from radar.** Urban flooding is hard to see in SAR (walls
  and water give bright double-bounce returns). Extents would be scored on
  open ground (fields, parks, roads) only, with a mask fixed before any
  model output is compared.
- **Tests that do not reuse the input.** The discharge at 3E-063 is the
  input, so the stage there is not a test. Independent checks: (1) the flow
  at which the model first puts water out of the channel at 3E-063, against
  the observed 20–24 m³/s at 301 cm; (2) the level at the Salto Grande
  station; (3) the Sentinel-1 extents.

## 4. Reach facts found while preparing the design (17 November 2026)

- **About 190 km² of ungauged land drains into the reach.** On the
  delineation DEM (GLO-30, 3 arc-seconds) the area is 1,141 km² at 3E-063
  and 1,333 km² at the Salto Grande station, about 6 km downstream along the
  river. Tributaries join about 1.3 km below the gauge (27 km²), **3.0 km
  (107 km²)**, 4.9 km (8 km²), 5.2 km (43 km²) and 5.7 km (4 km²). Distances
  follow the 90 m flow path and are approximate. SIBH has no flow station on
  any of these tributaries. Above the gauge, nothing larger than 5.5 km²
  joins within 3 km. That is 14% of the area at the downstream end, and a larger share
  of the flood flow, because most of the area above Atibaia is behind the two
  dams.
- **The reach is flat.** The 90 m surface model reads 739–745 m along 9 km of
  river below the gauge. No fall or dam shows at that resolution, and the
  Salto Grande plant's structure has not been located.
- **The two stations above the plant are one instrument.** ANA 62671200 and
  SAISP 814 ("CPFL – PCH Salto Grande – Montante") report identical levels in
  January 2021. In September 2026, 814 reports values of 34,749–49,232 (a
  different unit or a fault) and zero discharge on some days; 62671200 looks
  normal.
- **The downstream end can rise far more than the town gauge.** On 13
  September 2026, 62671200 reached 495 cm against 374 cm in January 2021,
  while the town gauge was 377 against 356 cm. Either the tributaries carried
  much more water in 2026, or the plant was operated differently. Either way,
  the downstream boundary and the tributary inflow are the two largest
  unknowns.
- **3E-063's overbank discharge rests on one unrevised curve.** SP Águas
  published 25 rating curves for 3E-063 (2002–2020). The low-flow segment
  changes with each revision (zero-flow stage 0.6–1.05 m). The segment above
  about 3.3–3.7 m is the same equation in every revision since 2002,
  Q = 13.5 (h − 2.0)^1.78. So flows above the overflow level are probably
  extrapolated, not measured.
- **No open high-resolution terrain was found for Atibaia.** São Paulo city's
  lidar (GeoSampa, 2017 and 2020) does not reach it. The municipality, the
  state cartographic institute and CPFL (whose plant licence would have
  required surveys of the river) are the places to ask.
- **Building footprints exist at high resolution.** OpenStreetMap (about
  31,600 buildings in the pilot window), Microsoft's footprints, and Google's
  Open Buildings 2.5D (0.5 m, with heights) all cover the town
  (`web/tools/build_buildings.mjs`).
- **Terrain-corrected radar is ready-made.** Planetary Computer's
  `sentinel-1-rtc` collection (CC BY 4.0, from October 2014) has VV and VH
  backscatter on a 10 m grid for the wide-swath passes; it was confirmed for
  five of the flood dates above. It does not include the Stripmap passes,
  which would need processing from raw GRD scenes.

## 5. Which model: LISFLOOD-FP, SFINCS or ANUGA

**What resolution can buy here.** A finer model helps only where its input is
real. Here the building footprints and the river line are fine; the ground
is not. ANADEM's 30 m heights carry errors of metres, while the floods in the
section 2 table stand 0.1–0.8 m above the overflow level. On flat ground, an
error in ground height that large moves the flood edge by tens of metres or
more. So the decisive improvement would be better ground heights, not a
finer model. A model that can carry fine buildings and channel on top of
coarse ground is still worth having, and the radar sees 10–20 m features.

| | SFINCS | ANUGA | LISFLOOD-FP |
| --- | --- | --- | --- |
| What it is | Deltares; reduced-physics (local inertial) 2D model for coastal, river and rain flooding | Full 2D shallow-water equations, finite volume on a triangular mesh | Bristol/Sheffield; raster 2D model, local inertial (ACC) or full shallow-water solvers |
| Current version | v2.5.0, November 2026 | 4.2.0, 13 November 2026 | 8.2 official (8.3 is a separate release) |
| Licence | Source GPL-3.0; the Windows executable is Deltares freeware | Apache-2.0 | GPL (v2 on Zenodo, v3 on project pages) |
| Windows | Ready-made executable | pip wheels for Python 3.10–3.14 | Build from source with Visual Studio |
| How it handles fine detail on coarse cells | **Subgrid tables**: computes on coarse cells while volumes and conveyance come from a fine DEM; quadtree refinement declared stable in v2.5.0 | **Variable mesh**: small triangles in town and along the channel, large elsewhere; buildings as holes or raised ground | **Subgrid channel** for rivers narrower than a cell; floodplain at grid resolution |
| River inflow, tributaries | Discharge source points | Inlet operator (discharge into a region) | Point or boundary inflow |
| Downstream boundary on a river | Water-level boundary; the river-specific option added in v2.3.0 was marked alpha/beta | Time-varying stage or transmissive boundaries (not confirmed from the docs) | Free (normal depth), fixed or time-varying level |
| Structures (the plant's weir) | Weirs, thin dams, culverts, gates | Weir, culvert and custom head–discharge operators | Weirs in older versions; not confirmed for 8.x |
| Speed for 25 floods with ensembles | Very fast; built for many runs | Slowest: the smallest triangle sets the time step (rough estimate: tens of minutes to hours per event on CPU at 5 m triangles in town) | Fast on CPU at 30 m; slower at fine raster resolution |
| Outputs | NetCDF maps (including maximum level), point series | SWW (NetCDF) on the mesh, maximum quantities | ASCII rasters, point series |

- **SFINCS fits the data best.** Its subgrid mode matches what exists: a
  fine composite DEM (ANADEM ground, the channel cut in from its width and
  the depth implied by 3E-063's zero-flow stage, buildings raised from
  footprints) carried by coarse compute cells. It is fast enough for the
  ensembles this reach needs, because the tributary inflow, the downstream
  level and the overbank discharge are all uncertain. It runs on Windows
  without building anything. Two cautions: its river-specific downstream
  boundary was marked alpha/beta when added, and how it treats buildings
  inside subgrid tables could not be confirmed from the documentation.
- **ANUGA is the better physics, but not the limiting factor yet.** Full
  shallow-water equations, buildings as mesh holes and real structure
  operators pay off when the ground is surveyed. On 30 m ground with slow
  floodplain flow, the extra physics changes little and the cost is many
  times higher. It becomes the first choice if lidar or survey data for the
  town turn up. Being a Python package, it would also sit most naturally in
  the pipeline.
- **LISFLOOD-FP remains possible** and has the longest record of comparison
  with radar flood extents. It offers less here: no subgrid treatment of the
  floodplain or buildings, a Windows build from source, and an unclear
  licence version.
- **Avoid rain-on-grid for the tributaries.** SFINCS and ANUGA can both turn
  rainfall into runoff on the grid. That would bring back the rainfall-runoff
  modelling that failed four times in this pilot. Tributary inflow should be
  scaled from measured flow, with its uncertainty run as an ensemble.

All three need a geospatial preprocessing step (reprojection, burning the
channel and buildings into a fine DEM, reading the radar). That is beyond the
standard-library pipeline, although `web/tools/lib/raster.mjs` already reads
the cloud-optimised GeoTIFFs these sources use.

## Sources

- SIBH public API: station records `/v1/station_prefixes/30863` and
  `/v2/stations/30863` (thresholds), hourly and daily measurements for
  stations 30863 (3E-063), 14585 (62671200) and 15161 (62669900, no records
  returned for these dates). Responses were saved only as temporary files,
  not in `data/raw/` or the manifest; a pipeline step would fetch them
  properly.
- Sentinel-1 GRD and Sentinel-2 L2A catalogue: Microsoft Planetary Computer
  STAC API, searched over 46.62–46.50 °W, 23.16–23.06 °S.
- Flood reports: Climatempo, 17 and 26 January 2017
  (https://www.climatempo.com.br/noticia/2017/01/17/chuva-em-sp-rio-atibaia-transborda-6663,
  https://www.climatempo.com.br/noticia/2017/01/26/rio-atibaia-campinas-e-jaguari-em-emergencia-7171);
  an ABRHidro conference paper on recurring overflows in Atibaia in 2011
  (https://files.abrhidro.org.br/Eventos/Trabalhos/148/056.pdf). Found by web
  search and not read in full.
- Place names: OpenStreetMap Nominatim.
- Models: SFINCS documentation and repository (sfincs.readthedocs.io,
  github.com/Deltares/SFINCS, its release notes and docs folder); ANUGA
  documentation, repository and package pages (anuga.readthedocs.io,
  github.com/anuga-community/anuga_core, pypi.org/project/anuga); LISFLOOD-FP
  as in `docs/model_design_hydraulic_run1.md`. Read on 17 November 2026; the
  HydroMT-SFINCS documentation site returned no content.
- Terrain search: São Paulo city's lidar notes
  (https://gestaourbana.prefeitura.sp.gov.br/?p=32643,
  https://spamlab.iag.usp.br/blog/pmsp_lidar/); nothing found for Atibaia.
