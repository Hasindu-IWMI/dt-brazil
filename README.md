# Upper Atibaia water-security pilot

First increment of the Brazil river-basin digital twin, for the upper Atibaia
sub-basin of the Cantareira / PCJ system (São Paulo). It is built on open data
only and currently does one thing: **replay observed daily records in 3D, with
a small set of clearly labelled derived diagnostics.**

It is not a digital twin. Inflow models were built and tested four times and
none passed validation. A flood model of Atibaia town was built and stopped at
its data check, before any model test. So nothing modelled is shown; there is
no forecast and no live feed.
See "What is and is not here" below.

## Run it

```bash
npm --prefix web install
```

The display basemap (30 m terrain, Sentinel-2 imagery, WorldCover land cover;
about 16 MB) is not in git. Build it once after cloning; it reads the open
sources directly and takes a few minutes. Without it the viewer still runs,
with the 90 m terrain and elevation colours.

```bash
npm --prefix web run basemap
```

The 3D buildings are built the same way: about 536,000 footprints from
OpenStreetMap and Microsoft, heights from OSM tags and Google 2.5D. It downloads
about 300 MB into `web/.cache/` (kept for rebuilds), reads Google's height
rasters in place, takes 30–60 minutes and writes about 15 MB of tiles. Without
them the viewer runs with no buildings.

```bash
npm --prefix web run buildings
```

```bash
npm --prefix web run dev
```

Then open http://localhost:5173. Drag to orbit, scroll to zoom, use the slider
or Play to move through time, click the chart to jump to a date.

The card at the top left switches between two styles:

- **Realistic** (default) is Sentinel-2 imagery on the full-resolution
  Copernicus DEM at true scale. It is lit by the computed sun for the replayed
  date at the chosen hour, with a sky, height haze and reflective lakes.
- **Analytical** is the original look: elevation colours, lakes coloured by
  observed storage, and storage columns.

The card also sets the vertical scale (true scale to ×4), haze and layers,
including ESA WorldCover land cover and 3D buildings. Buildings appear when you
zoom in to a town (closer than about 9 km); "Go to" flies to one. Hover a
building to see where its footprint and height come from. URL options: `?style=analytical`,
`?relief=2`, `?hour=16.5`, `?haze=hazy`, `?quality=high|medium|low` (mesh
density; chosen from the GPU by default).

### Realistic display: what is data and what is display

The approach follows the Kelani WebTwin (`DT Kelaniya/webtwin/docs/REALISM_AND_XR.md`):
data first, display second, and every display assumption labelled.

| Element | Data (unchanged) | Display only |
| --- | --- | --- |
| Terrain | Copernicus GLO-30 heights at 30 m (a surface model: forest canopy included), EGM2008 | Vertical exaggeration; mesh drawn every 60 m (90 m on integrated GPUs) with 30 m relief shading |
| Ground colour | Sentinel-2 L2A, median of four cloud-free dates in August 2024 (`web/public/data/imagery.json` lists the scenes) | Display stretch; colour fades to the mean image colour at the window edge |
| Land cover layer | ESA WorldCover 2021 classes | Legend colours; water pixels drawn smoother (they catch the sun) |
| Lakes | OpenStreetMap outlines | Drawn at the DEM's own lake surface with sky reflection and ripples. **Not** the observed level or extent on the replay date: no bathymetry is public, and the reservoir level datum is not tied to the DEM's |
| Sun | Solar position for the window centre, replayed date, chosen hour (UTC−3; the daylight-saving hour before 2019 is ignored) | Twilight lighting when the sun is below the horizon |
| Sky and haze | none | Preetham sky scaled to the scene's exposure; haze colour from the same sky model; "Clear" and "Hazy" are looks, not observations |
| Storage | Observed % stored (ANA SAR), shown in labels, colours and columns | Column height scale |
| Buildings | Footprints: OpenStreetMap, else Microsoft ML footprints where no OSM building overlaps. Height: OSM `height`, else `building:levels` × 3 m, else Google Open Buildings 2.5D 2023 (a model estimate: median of the 2 m pixels in the footprint), else a 4 m placeholder. Counts per source: `web/public/data/buildings.json` | Roof form (hipped, gabled, shallow shed or flat with a parapet; the ridge is never above the data height), windows, doors, paint, roof material (ceramic tile, metal, fibre-cement, concrete) and weathering are procedural. Bases sit on the drawn terrain, which is a 30 m surface model. Shadows are baked on the ground from the current sun. The Analytical style colours buildings by height source instead. Buildings are today's, not the replayed date's |
| Rain, rivers, tunnels | Audited daily rain at each gauge; daily discharge at the SIBH river gauges and tunnel outlets; the DEM catchments of the two gauges above the lakes (teal); the direction of each mapped river (OpenStreetMap draws waterways downstream) | Flat symbols of a fixed size on screen: dot area ∝ rain (capped at 80 mm), ring area ∝ discharge (capped at 55 m³/s); flow particles drift downstream across each river's width (Rio Atibaia 11 m from its OSM width tag, a nominal 12 m elsewhere, never under 7 px on screen), faster mid-channel, at a display rate that is **not a velocity**; the mapped river lines are a separate layer, off by default; **tunnel routes are schematic arcs** between the known ends (a station, or else the nearest shore of the connected reservoir) |
| Floods, Atibaia town | The highest hourly river level each day at SP Águas' gauge 3E-063, on its own zero, and SP Águas' official alarm levels there (attention 2.40 m, alert 2.61 m, emergency 2.80 m, overflow 3.01 m); the level 4 km downstream (ANA 62671200); the Geological Survey of Brazil's risk sectors of 2012 | A flat diamond at the gauge in the colour of the alarm level reached, pulsing from the attention level up; its label carries a level bar marked with the alarm levels. ANA's gauge 62670000, 77 m away, is the white dot. The diamond has a fixed size and is **not a flood extent**. Risk sectors are painted on the terrain by type (river flood blue, flash flood teal, landslide brown; stronger for very high risk). No modelled water |

The imagery and land cover show one season and do not change with the replay
date. During the 2014–15 crisis, the lakes on the ground imagery would have
looked very different.

## Refresh the data

Python 3.10+ with the standard library only; Node 22 or later (CI uses 24).

```bash
python -I pipeline/run_all.py --fetch
```

This runs every download (resumable) and then every build step in order:
reservoirs, river gauges, ANA rain, SIBH telemetric rain, SIBH river, dam and
tunnel stations, the two flood stations at Atibaia town, CPRM's risk sectors
(once), then `process.py`, `sibh_rain.py`, `rain_alignment.py`,
`audit_rain.py`, `forcing.py`, `sibh_flow.py`, `upstream_catchments.py`,
`cprm_risk.py`, `flood_gauges.py` and `viewer_layers.py`. Each step's output is also
written to `data/logs/run_all_<step>.log`. Without `--fetch` it only rebuilds
from what is on disk; `--refresh` also re-fetches the most recent records;
`--scene` re-fetches the map outlines from OpenStreetMap. It never runs the
model scripts (see "Frozen analyses" below).

The display basemap (30 m terrain, Sentinel-2 imagery, WorldCover land cover)
and the 3D buildings do not change with new records, are not committed, and
are built separately (the deploy workflow does this too):

```bash
npm --prefix web run basemap
```

```bash
npm --prefix web run buildings
```

The building step caches its downloads in `web/.cache/buildings/`; add
`-- --refresh` to fetch them again. Overpass refuses queries when it is busy;
the step retries, and can simply be run again (fetched OSM blocks are kept).
`-- --no-osm` builds from the Microsoft footprints alone.

The reservoir and ANA services are slow and time out; the fetches are
resumable, so run again until no `FAIL` lines remain. Every download is logged
with URL, size and SHA-256 in `data/raw/manifest.jsonl`.

## Tests, build and automation

```bash
python -I -m unittest discover -s tests -v
```

The tests cover the parsers and processing rules, and check the committed data:
dates unique and sorted in every series, viewer arrays aligned, the 2015
storage low still in place, and **no modelled series in the viewer unless that
model was accepted**.

```bash
npm --prefix web run build
```

This writes a static site to `web/dist` that works from any folder or URL
path; `npm --prefix web run preview` serves it at http://localhost:4173.

GitHub Actions (`.github/workflows/`):

| Workflow | When | What |
| --- | --- | --- |
| `ci.yml` | Every push to `main` and every pull request | Tests and the static build |
| `refresh-data.yml` | Mondays, or by hand | `run_all.py --refresh`, tests, then opens a pull request for a person to review. It never merges. Needs Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests" |
| `deploy-viewer.yml` | By hand only | Publishes `web/dist` to GitHub Pages (Settings → Pages → Source: GitHub Actions). On a public repository the site is public |

## Frozen analyses

`model.py`, `model_run3.py`, `model_run4.py` and `investigate_runoff.py` document
experiments already made. They read `forcing_*.csv`, which now includes the
SIBH telemetric gauges, so re-running them would not reproduce their reports.
The inputs they used are kept: `forcing_*_v1_unaudited.csv` (run 1) and
`forcing_*_v2_ana_only.csv` (runs 2–4 and the runoff investigation), with
`rain_exclusions_v1_ana_only.json`, `docs/rain_audit_v1_ana_only.md` and
`docs/forcing_report_v2_ana_only.md`. A new model run needs its own design,
fixed before it is run.

The flood run (see "Flood model of Atibaia town, run 1" below) is kept the
same way. Its scripts are not part of `run_all.py`.
- **Standard-library scripts:** `fetch_flood_stations.py`,
  `fetch_s1_passes.py`, `flood_passes.py`, `fetch_anadem_window.py`,
  `fetch_flood_landcover.py`, `flood_terrain.py`, `flood_channel.py`, and the
  reader `cogread.py` they share.
- **Scripts that need the `atibaia-sfincs` conda environment**
  (`envs/flood-sfincs.yml`): `flood_build_model.py` (SFINCS, set aside),
  `flood_sfincs_smoke.py`, `flood_lisflood_build.py`, `flood_benchmark.py` and
  `flood_radar_maps.py`. On Windows, take any other GIS stack (OSGeo4W) off
  PATH first; see the environment file.
- **Docker images:** LISFLOOD-FP runs from `atibaia/lisflood-fp:8.2`, built
  from `envs/lisflood-fp.Dockerfile`; SFINCS from Deltares' image. The radar
  maps have been made, so re-running any of this would no longer be a blind
  test.

## Layout

| Path | Contents |
| --- | --- |
| `pipeline/` | Acquisition and processing scripts (Python, standard library); `run_all.py` runs them in order |
| `data/raw/` | Downloads exactly as received (SIBH responses gzip-compressed), plus the manifest |
| `data/processed/` | Tidy CSVs: one per reservoir and gauge, system totals, control point, catchment forcing |
| `docs/` | Generated reports: data quality, rain audit, SIBH rain gauges, rain day alignment, SIBH flow stations, forcing, model validation |
| `tests/` | Unit tests and data checks (standard library `unittest`) |
| `envs/` | The conda environment (with lock files) and the LISFLOOD-FP Dockerfile used by the flood run |
| `models/` | Model folders written by the flood-run scripts. Not committed: rebuilt by the scripts; results that matter are in `docs/` and `data/processed/` |
| `web/` | Three.js viewer (Vite). `web/public/data/` holds what it reads |
| `.github/workflows/` | CI, weekly data refresh, manual viewer deploy |

## Sources

| Data | Source | Type | Licence / terms |
| --- | --- | --- | --- |
| Reservoir level, storage, inflow, release (daily) | ANA SAR, Cantareira module | Observed, operator-reported | None shown on the page |
| River discharge (daily) | ANA HidroSerieHistorica web service | Observed stage, rating-curve discharge | Not stated |
| Rain, conventional gauges (daily) | ANA HidroSerieHistorica web service | Observed, read at 07:00 | Not stated |
| Rain, telemetric gauges (10-minute, fetched as hourly sums) | SP Águas SIBH public API; gauges of SP Águas, Sabesp, CEMADEN, SAISP and IAC | Observed, unconsolidated | None shown; portal footer reads "todos os direitos reservados" |
| River stage and discharge, reservoir and channel levels, tunnel flows (10-minute, fetched as hourly means) | SP Águas SIBH public API; stations of SP Águas, Sabesp and SAISP, some fed from ANA's telemetry | Observed, unconsolidated; discharge from rating curves | As above |
| Air temperature (daily, for evapotranspiration) | NASA POWER (MERRA-2) | Reanalysis | Free with attribution |
| Terrain | Copernicus DEM GLO-30 (ESA): 3 arc-seconds for delineation, 1 arc-second (30 m) for display | Satellite surface model, EGM2008 | Free with attribution |
| Ground imagery | Sentinel-2 L2A (ESA Copernicus) via Element 84 Earth Search; August 2024 cloud-free median | Satellite, display basemap | Free and open; "Contains modified Copernicus Sentinel data 2024" |
| Land cover | ESA WorldCover 10 m 2021 v200 | Satellite-derived classes | CC BY 4.0 |
| Lake outlines, rivers | OpenStreetMap via Overpass | Mapped | ODbL 1.0 |
| Building footprints | OpenStreetMap via Overpass; Microsoft Global ML Building Footprints where OSM has none | Mapped; machine-detected from imagery | ODbL 1.0 |
| Building heights | OSM `height` and `building:levels` tags; Google Open Buildings 2.5D Temporal v1, 2023 | Mapped; model estimate from Sentinel-2 | ODbL 1.0; CC BY 4.0 |
| Operating bands | Joint Resolution ANA/DAEE 925/2017, as tabulated by Comitês PCJ | Regulation | Public |
| Bare-earth terrain (flood run) | ANADEM v1 (ANA / UFRGS; Laipelt et al. 2024), zone 23K, a window read by byte ranges | Terrain model derived from Copernicus GLO-30 | Public |
| Radar backscatter (flood run) | Sentinel-1 RTC, VV, via Microsoft Planetary Computer (`sentinel-1-rtc`) | Satellite, terrain-corrected | CC BY 4.0; contains modified Copernicus Sentinel data |
| River width (flood run) | OpenStreetMap `width` tag on the Rio Atibaia (Sentinel-2 bands B03/B08 were tried first) | Mapped | ODbL 1.0 |
| Flood and landslide risk sectors, Atibaia | Serviço Geológico do Brasil (CPRM), "Ação emergencial para delimitação de áreas em alto e muito alto risco a inundações e movimentos de massa: Atibaia, São Paulo", November 2012; RIGEO doc/20208, GIS file `sig_atibaia_sp_risco.zip` only | Official mapped areas from a field survey; not flood extents; not updated since 2012 | Public repository; licence not checked |

## What is and is not here

Observed and shown as-is: reservoir level, useful volume, inflow and release;
river flow at four gauges; the river level at Atibaia town (SP Águas 3E-063)
and 4 km downstream (ANA 62671200), each day's highest hourly reading. Gaps
are shown as "no data" and never filled. At 62671200, hourly readings above
10 m are dropped as faults (four days read 45 to 460 m); December 2015 there
reads 5 to 9 m while the town gauge stays below 3.2 m, which is unexplained
and kept. Official, as published: SP Águas' alarm levels at 3E-063 and the
Geological Survey of Brazil's 2012 risk sectors.

Derived, and labelled as derived on screen:

- System storage = sum of the four reservoirs, as % of 981.56 hm³.
- Operating band = the band whose threshold that percentage meets (shown only
  from June 2017, when the rules took effect).
- Implied net export = total inflow − total release − storage change. A
  residual that lumps the withdrawal to São Paulo with transfers received,
  evaporation and measurement error. It is not a measurement.
- Local inflow = flow at the Atibaia gauge − releases from Cachoeira and
  Atibainha, same day.
- Floods at Atibaia town = runs of days whose highest hourly level at 3E-063
  reaches the overflow level (3.01 m), joined when less than 10 days apart:
  47 from January 2015 to 16 November 2026. The flood check
  (`docs/flood_option_check.md`) counted days by their mean level, so it
  found fewer (30 floods since October 2014). The last flood, peaking on
  14 November 2026, is after the viewer's last date, which the reservoir
  record sets.

Deliberately absent, because the open data cannot support it:

- **Lake extent or depth by date.** No bathymetry is public, so lake outlines
  are fixed map outlines and storage is shown by a bar in each lake's label, and
  in the analytical style by colour and a column.
- **The withdrawal to São Paulo, Tunnel 7 and the Paraíba do Sul transfer.**
  Not published. Tunnel 5 and Tunnel 6 flows are public on SIBH and are now in
  the pipeline (see "River, dam and tunnel stations" below), but SIBH has only
  levels at Tunnel 7 and at the Paraíba do Sul pumping station, and its two
  transfer stations return no data. The viewer shows Tunnels 6 and 5.
- **Measured outflow from the dams.** Sabesp's stations at both dams hold the
  reservoir level and the level in the downstream channel, not a discharge.
- **Sub-daily data.** ANA's public telemetry returns nothing for these gauges.
  The state network (SIBH) has 10-minute rain and river data, used here only
  as daily totals and daily means.
- **Any simulated or forecast value.** The inflow models failed validation,
  and the flood model stopped before its test (both below), so neither is
  shown. The Sentinel-1 flood maps made for the flood test are not shown
  either: the design allowed that only if its data check passed.
- **How far the water spread on any day in Atibaia.** Nothing here measures
  it: the gauge gives a level at one point, the risk sectors are where people
  were at risk in 2012, and the flood model, which would have drawn extents,
  stopped before its test. Modelled water will be shown only if a second flood
  run passes a test designed before it is run. The display for it is built
  (below), but has nothing tested to show.

- **Restoration or land-use effects.** No defensible basis yet.

### Modelled flood water in the viewer (built, nothing to show yet)

The viewer can draw a flood run's water: the wet cells draped 1 m over the
drawn terrain, coloured by depth (light shallow, dark deep, with the lakes'
ripples and sky reflection), and particles carried by the modelled velocity,
coloured by speed (white slow, yellow, orange 1.5 m/s and faster) and sped up
to be visible (the legend gives the factor). Hovering gives the depth, speed
and direction at a point. While water is shown, the risk sectors are drawn as
dashed outlines, since both are blue.

`pipeline/flood_water_viewer.py` converts LISFLOOD-FP grids (UTM 23S) to the
viewer's lon/lat grid. It writes the published file
(`web/public/data/flood_water.json`) **only for a run whose verdict file says
it passed its test**, and refuses otherwise; the viewer, in turn, shows a
published file only if it says `accepted: true`. Untested output can be
written with `--test` to `web/dev-data/` (git-ignored, never built) and seen
only in the development server with `?floodtest=1`, under a red TEST RENDER
banner. The display was checked that way on flood run 1's steady 15 m³/s
LISFLOOD-FP test run (in-bank, not a flood: 1.02 km² wet, mostly still water
in hollows, the over-flooding run 2 must fix). That run saved no velocities,
so the check used a velocity derived from the modelled water-surface slope
(Manning's equation); **flood run 2 must save the model's own velocities**
(LISFLOOD-FP writes them when asked) for the particles to show modelled flow.

## Checks already passed

- The lowest system storage in the record is −23.3% of useful volume on
  2 February 2015, the documented low point of the 2014–15 crisis.
- The implied net export sits at 30–32 m³/s (yearly medians) in 2009–2013,
  beside the roughly 31 m³/s the system was known to send to São Paulo, and
  never exceeds the band limit on any day from June 2017 to 2024.
- Gauges just below each dam, run by other agencies, track the reported
  releases over 1984–2026 (correlation 0.90 for Cachoeira, 0.86 for Atibainha).
- Reported percentages agree with reported volumes on every reservoir-day once
  the capacity in force at the time is used (see below).
- SAR's reservoir level matches the 07:00 reading of Sabesp's telemetric
  gauge at the dam, as served by SIBH, to within 5 cm on 99% of days at
  Cachoeira (from 2015) and 98% at Atibainha (from 2010), with a median
  difference of 0.000 m (`docs/sibh_flow_report.md`).

## Data gaps: what was fixed and what remains

Fixed or explained:

- **Reservoir history.** Now complete from 1 January 1984 to the present for
  Jaguari-Jacareí, Cachoeira and Atibainha (15,658 days each, none missing).
  Queries for 1982–83 return no rows. The earlier failure was the service
  timing out, not missing data.
- **Percentage versus volume mismatch.** Not an error. The source changed its
  reference capacities several times (last on 1 April 2010). The pipeline
  recovers the capacity in force per month from the records and uses it.
- **Placeholder values.** Raw gauge series carry 100000.0 on some days; these
  are rejected and counted.

Still open (cannot be settled from open data):

- **Paiva Castro has no records for 2000–2003** (1,461 days), so system totals
  are missing for those years.
- **Gauge below release.** ANA's Piracaia gauge (62665000) reads more than
  0.5 m³/s below the Cachoeira release on 50 days or more in 2010, 2017–2019,
  2022 and 2025. A one- or two-day shift does not fix it. SIBH's stations
  narrow it down (`docs/sibh_flow_report.md`, section 4):
  - In most years the water did leave the dam. On ANA's shortfall days the
    river 1 km below the dam (SP Águas 3E-116, a water level, so no rating
    curve is involved) stands as high as on other days of the same year with
    the same reported release: a median of 1 cm lower over 2010–2026 (−1.0 cm
    in 2018, −0.5 cm in 2025), where a 0.5 m³/s step in release moves it about
    12 cm. So the water goes missing downstream of that point, or not at all.
    In 2025 the telemetric gauge beside ANA's (3E-145) reads short on 13 days
    against ANA's 89, which points at ANA's record itself, most likely its
    rating.
  - 2022 may be different. 3E-145 also reads short that year (108 days), and
    on its shortfall days the river below the dam was 8 cm lower. That
    suggests less water was released than reported, but it rests on one group
    of 102 days with the same reported release.

  Still needs ANA's rating history for 62665000 and Sabesp's measured outflow
  to settle.
- **Capacities before 2000 differ a lot** (Atibainha 130 hm³, Paiva Castro
  27.6 hm³, against 96.25 and 7.61 today). Volumes across revisions are not
  strictly comparable; long-term storage trends should be read with care.
- **Jaguari-Jacareí shows about 599 hm³ capacity for Jan–Aug 2004**, between
  two periods at about 808. Unexplained.
- **The Atibaia gauge record ends on 31 May 2026**; other mid-river gauges end
  in 2022. SIBH's telemetry for the river above and below the dams is in the
  pipeline. At the Atibaia gauge's own site, SP Águas' telemetric station
  3E-063 (110 m from ANA's) is now fetched hourly from 2015 for the flood run
  (`pipeline/fetch_flood_stations.py`). It is not yet in the daily series or
  the viewer. ANA's telemetric code there (62669900) returns no records for
  those years.
- **ANA's daily record at Atibaia (62670000) holds spurious high days.** On
  13–17 January 2021 it gives 89–110 m³/s, where 3E-063 at the same site
  recorded 20–30 m³/s and the station 4 km downstream 23–41 m³/s. The same
  happens on 4 February 2023 (103 against 38) and 5–6 January 2019 (85 and 82
  against 24 and 22). ANA's yearly volume is 24–25% above the telemetric
  record in 2021 and 2022. The frozen runoff investigation's "independent
  area" uses this record, so part of its post-2017 excess may come from these
  days (`docs/flood_option_check.md`, section 1).
- **Two ANA-network rain gauges carry the wrong day on some years**
  (`docs/rain_alignment.md`). Piracaia (2346094) is one day out on every year
  from 2018 to 2025. Joanópolis (2246090) changes between years. Both feed the
  catchment rain, which has **not** been corrected: that is a change to the
  forcing and needs a decision.
- **Band limit exceeded** by the implied export on 11 days in 2025 and 5 in
  2026. Unexplained.

See `docs/data_quality_report.md` for the full tables.

## Inflow model: built, tested, not accepted

A daily GR4J rainfall-runoff model was built for the inflow to Cachoeira and
Atibainha (`pipeline/gr4j.py`, `pipeline/model.py`), forced by ANA rain gauges
and Oudin evapotranspiration from NASA POWER temperature
(`pipeline/forcing.py`). Catchments were delineated from the terrain
(`pipeline/delineate.py`) and match ANA's published areas to within 1.3% at
both dams and 0.1% at the Atibaia gauge.

The acceptance test was written into `pipeline/model.py` before the first run:
calibrate on 2004–2013, then in each of three independent periods beat a
calendar-day benchmark, reach KGE ≥ 0.50 and keep volume bias within 25%.

**Neither model passed, so the viewer does not show modelled inflow.**

| Catchment | Calibration KGE | Drought 2014–16 | 2017 onward | 1986–2001 | Failed on |
| --- | --- | --- | --- | --- | --- |
| Cachoeira | 0.79 | KGE 0.57, bias +36% | KGE 0.75, bias +8% | KGE 0.68, bias +13% | Drought volume bias |
| Atibainha | 0.59 | KGE 0.54, bias +14% | KGE 0.08, bias −53% | KGE 0.39, bias −31% | Two periods |

What the failure points to (diagnosis, not a fix):

- **The catchments yield less water per unit of rain since 2014.** Observed
  runoff ratio fell from about 0.31–0.33 in 2004–2013 to 0.19 in 2014–2016 and
  0.22–0.29 since. A model tuned on 2004–2013 therefore overestimates drought
  inflow. This is the differential split-sample test doing its job.
- **Atibainha's rainfall input looks wrong after 2017**: 953 mm/yr for
  2018–2021 against 1,323 mm/yr at Cachoeira next door. One or more gauges
  probably under-record or carry unflagged gaps.
- **Low flows are overestimated severalfold** in every period.
- **The parameter ensemble is uninformative**: the 30 best sets are nearly
  identical, and under 1% of observations fall inside their spread.

The parameters were not re-tuned after seeing these results. Any revised model
is a new experiment and needs its own test fixed in advance, with the caveat
that the validation periods have now been seen.

## Rain gauge audit (after the model run)

`pipeline/audit_rain.py` compares each gauge with its neighbours, month by
month and year by year, using no model output. It flags a month whose total
is under 25% of the regional median (when that median is at least 50 mm), and
a year whose ratio to the region is outside 70–140% of the gauge's own usual
ratio. It found 65 such months and 20 such years across 18 gauges.

- **Piracaia (ANA, 2346094)** is the main fault: 451 mm in 2014, 633 in 2017,
  217 in 2018 and 214 in 2019, where neighbours recorded 950–1,300 mm. It also
  reads far too high in 2010 and 2016. 25 flagged months, 8 flagged years.
- **Crioulos (2346334)** reads 705 and 824 mm in 2018 and 2019, and too high in
  2014. 16 flagged months, 6 flagged years.
- **Atibaia (ANA, 2346095)** reads about half its neighbours in 2019 and 2021.
- Five gauges show no problem at all: Piracaia (SP Águas), both Joanópolis
  gauges, Atibaia (SP Águas) and Santa Isabel. Four more have isolated flags.

Both faulty gauges fed Atibainha's rainfall. With the flagged records treated
as missing, Atibainha's rain for 2018–2021 rises from 956 to 1,202 mm a year
and for 2017 from 1,041 to 1,169 mm; Cachoeira barely changes. `forcing.py`
now uses the audited records and keeps the unaudited value in a separate
column; the pre-audit forcing is saved as `forcing_*_v1_unaudited.csv`.

**The model has not been re-run on the audited rainfall.** The validation
table above is the pre-audit run. Coverage is also thin at the end of the
record: Cachoeira has one gauge or none on 775 days in 2022–2025 (fixed by the
SIBH telemetric gauges; see below).

Reports: `docs/model_validation_report.md`, `docs/forcing_report.md`,
`docs/rain_audit.md`.

## Inflow model, run 2 (audited rainfall): still not accepted

Run 2 changed one thing only, the rainfall input. Model, parameter bounds,
search, periods and acceptance criteria were identical and restated in
`pipeline/model.py` before the run. The validation periods had been seen once
in run 1, so run 2 is not a blind test.

| Catchment | Period | Run 1 | Run 2 | Passed in run 2 |
| --- | --- | --- | --- | --- |
| Cachoeira | Calibration 2004–2013 | KGE 0.79 | KGE 0.81 | – |
| Cachoeira | Drought 2014–2016 | KGE 0.57, bias +36% | KGE 0.61, bias +30% | No (bias) |
| Cachoeira | 2017 onward | KGE 0.75, bias +8% | KGE 0.75, bias +7% | Yes |
| Cachoeira | 1986–2001 | KGE 0.68, bias +13% | KGE 0.67, bias +12% | Yes |
| Atibainha | Calibration 2004–2013 | KGE 0.59 | KGE 0.70 | – |
| Atibainha | Drought 2014–2016 | KGE 0.54, bias +14% | KGE 0.74, bias +14% | Yes |
| Atibainha | 2017 onward | KGE 0.08, bias −53% | KGE 0.35, bias −31% | No |
| Atibainha | 1986–2001 | KGE 0.39, bias −31% | KGE 0.44, bias −32% | No |

Both expectations written before the run held: Atibainha improved, and
Cachoeira's drought bias remained. **Neither model is accepted, and the viewer
still shows no modelled values.**

What this establishes: the rain-gauge faults were real and fixing them helped,
but they were not the main obstacle. The share of rain that becomes inflow is
not stable across decades (Atibainha: about 0.41 in 1986–2001, 0.33 in
2004–2013, 0.19 in 2014–2016, 0.29 since), and a model with fixed parameters
cannot follow that. Atibainha's production-store parameter also sits on its
upper bound in both runs, a sign the model structure is straining.

Run 1 is archived as `docs/model_validation_report_run1_unaudited.md`.

## Why the runoff share changes (investigation, no modelling)

`pipeline/investigate_runoff.py` compares three areas by water year: the two
operator-computed reservoir inflows, and an independent 351 km² area between
the dams and the Atibaia gauge measured only by river gauges.

| Question | Evidence | Verdict |
| --- | --- | --- |
| Is the 2014–16 collapse an artefact of the operator's inflow accounting? | The independent area fell just as far: runoff share 0.33 → 0.17, against 0.31 → 0.19 (Cachoeira) and 0.32 → 0.20 (Atibainha) | **No.** The collapse is real |
| Does climate alone explain it? | A climate-only (Budyko) estimate predicts 0.20–0.24 for 2014–16. It matches Atibainha, but Cachoeira yielded 25% less and the independent area 40% less than predicted | **Mostly.** Less rain and more evaporation demand explain most of the drop, not all |
| Is there catchment memory? | Yearly runoff share correlates 0.37–0.39 with the previous two years' rain in two areas, 0.22 in the third | **Weak to moderate support** |
| Are Paraíba do Sul transfers counted as Atibainha inflow? | Atibainha's inflow relative to Cachoeira's was lowest (0.68) in 2018–2021, when the link started | **Not supported** |
| Is the operator's older inflow record sound? | Atibainha shows a runoff share of 0.42 in 1986–2001 (0.63 in 1996), a third above the climate estimate; the independent area shows 0.36 for 1985–1991 | **Doubtful before 2000**, unresolved |

Also visible: since 2017 Atibainha and the independent area yield 16–39% more
runoff than the climate estimate allows, which suggests their rainfall is
still underestimated (few gauges remain).

Limits: the climate estimate is a one-parameter curve applied to means of
three to sixteen years; evaporation demand comes from reanalysis temperature;
the independent area is a difference of three gauges and has only 20 usable
water years.

What it means for the pilot:

- A daily model with fixed parameters, calibrated on wet years, will
  overestimate drought inflow here. A defensible model must be calibrated
  across the drought and judged on it, and may need a slow groundwater store.
- The runoff share swings between 0.13 and 0.41 from year to year at Cachoeira
  for climatic reasons. Any effect of restoration on water yield would have
  to be detected against that, which these records cannot do.

Report: `docs/runoff_shift_investigation.md`.

## Inflow model, run 3: no structure accepted

Design and test were fixed and approved in `docs/model_design_run3.md` before
any code was written: GR4J and GR5J, calibrated on one climate regime and
judged on the other, in both directions, against four criteria. It was not a
blind test. Results: `docs/model_validation_report_run3.md`.

| Catchment | Window (GR4J) | Daily KGE | Volume bias | Monthly KGE | Low-flow bias | Passed |
| --- | --- | --- | --- | --- | --- | --- |
| Cachoeira | Fold 1 validation, 2014–2026 | 0.66 | +12% | 0.66 | +158% | No (low flow) |
| Cachoeira | Fold 2 validation, 2004–2013 | 0.75 | −8% | 0.85 | +104% | No (low flow) |
| Cachoeira | 1986–2001, fold 1 parameters | 0.50 | +12% | 0.51 | +79% | No |
| Atibainha | Fold 1 validation, 2014–2026 | 0.55 | −22% | 0.61 | +139% | No (low flow) |
| Atibainha | Fold 2 validation, 2004–2013 | 0.29 | +22% | 0.28 | +174% | No |

- **Cachoeira now meets three of the four criteria in both folds**, including
  the drought volume bias that sank runs 1 and 2 (+36% and +30% before, +12%
  now). It fails only the low-flow criterion, and misses on the early record.
- **GR5J brought nothing**: mean validation KGE 0.563 against 0.562 for GR4J.
  The expectation written beforehand, that it would cut the drought bias, was
  wrong; the square-root objective did that for both structures.
- **Atibainha fails outright** when calibrated on the dry years and tested on
  the wet decade (KGE 0.29), and one parameter sits on its lower bound.
- **The low-flow overestimate is there even in calibration** (+128% to +160%),
  so the models cannot fit the lowest fifth of days at all.

One diagnostic run afterwards compared the record's median day-to-day change
(1.12 m³/s) with its low flows (1.09 m³/s) and called the record noisy.
**That comparison was wrong**: it mixed real variability with noise. A valid
test on rainless spells (in `docs/model_design_run4.md`) does show large
measurement noise: inflow rises on about half of all rainless days, with
anti-correlated daily changes, implying an error of about 1 m³/s per day.
Selecting the lowest fifth of single days therefore biases the observed low
flow downward. The run 3 criterion stands for run 3.

**Outcome, as the design said:** the pilot stays an observed-record tool. No
modelled inflow is shown in the viewer.

## Inflow model, run 4: not accepted; modelling on this record has stopped

Run 4 (`docs/model_design_run4.md`, approved before the run) re-scored the
run 3 GR4J parameter sets for Cachoeira with the low-flow criterion on 7-day
means, and narrowed the claim to 2004 onward. Nothing was recalibrated.
Results: `docs/model_validation_report_run4.md`.

| Fold | Validation window | Daily KGE | Volume bias | Monthly KGE | Low-flow bias, single days (run 3) | Low-flow bias, 7-day means (run 4) | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 (wet → dry) | 2014–2026 | 0.66 | +12% | 0.66 | +158% | +84% | No |
| 2 (dry → wet) | 2004–2013 | 0.75 | −8% | 0.85 | +104% | +36% | Yes |

- Removing the selection bias roughly halved the apparent overestimate, as
  expected, so part of run 3's failure was the badly designed criterion.
- The rest is a real fault: a model calibrated on the wet decade gives
  drought low flows of 1.49 m³/s where 0.81 m³/s was observed. Its dry-weather
  recession is too slow for drought conditions.
- The model calibrated on the dry years transfers to the wet decade within
  tolerance. The failure is one-directional: wet-calibrated models do not
  reach down to drought low flows.

The design ruled out a run 5 on this record, and none will be done. **The
pilot is an observed-record tool.** What would reopen modelling is new data,
not a new criterion: sub-daily or better rainfall (state network, CEMADEN),
the operator's measured flows, or new inflow records for a forward test.

## Telemetric rain gauges (SIBH), added 16 November 2026

SP Águas' SIBH portal (https://cth.daee.sp.gov.br/sibh/) has a public JSON
API with the 10-minute records of the telemetric rain gauges of SP Águas,
Sabesp, CEMADEN, SAISP and IAC. CEMADEN's own download is CAPTCHA-gated; this
route is not.

- `pipeline/fetch_sibh_rain.py` downloads hourly sums for the 38 gauges within
  20 km of either catchment centroid. It leaves out ANA's gauges, radar
  products and conventional gauges, which are already taken from ANA.
- `pipeline/sibh_rain.py` builds daily totals by rules fixed before any
  series was computed:
  - A day runs 07:00 to 07:00 local time and is kept only if all 24 hours are
    present; a missing hour is never taken as zero.
  - Which date it carries was settled by correlation with ANA gauges. Reading
    day won, with a median r of 0.39 against 0.25.
  - Co-located gauges count as one site.

  One rule was changed after a dry run on five gauges and before any use, and
  the change is recorded in the script. Report: `docs/sibh_rain_report.md`.
- 23 sites result. Sabesp's gauges at the Cachoeira and Atibainha dams are
  nearly complete from 2010, and the SP Águas gauge above Cachoeira from 2015.
  CEMADEN gauges lose many days to transmission gaps.
- They go through the same neighbour audit (`audit_rain.py`), which flags 36
  months and 1 year among them, mostly one CEMADEN gauge (Piracaia Dobrada)
  recording dry months. It also confirms the ANA flags from before: 64 of 65
  months, plus 9 new months and 1 new year in gauges already known to be
  faulty.

Effect on catchment rain (`docs/forcing_report.md`; the ANA-only version is kept
as `docs/forcing_report_v2_ana_only.md`):

| Catchment, period | Median gauges per day | Days with one gauge or none | Mean annual rain (audited) |
| --- | --- | --- | --- |
| Cachoeira 2014–2016 | 2 → 8 | 49 → 0 | 1,445 → 1,388 mm |
| Cachoeira 2022–2025 | 1 → 9 | 775 → 0 | 1,413 → 1,625 mm |
| Atibainha 2018–2021 | 2 → 8 | 39 → 0 | 1,202 → 1,226 mm |
| Atibainha 2022–2025 | 2 → 13 | 31 → 0 | 1,238 → 1,411 mm |

The thin coverage after 2022 is fixed. Since 2022 both catchments have had
about 14–15% more rain than the few remaining ANA gauges recorded. That fits
the earlier finding that Atibainha's runoff since 2017 was more than its
measured rainfall allowed. Before 2014 nothing changes much.

**The models were not re-run on this rainfall.** Runs 1–4 and the runoff
investigation are frozen (see "Frozen analyses"). A new run would need its own
design, fixed in advance, and should first settle the two mislabelled gauges
(`docs/rain_alignment.md`).

## River, dam and tunnel stations (SIBH), added 16 November 2026

The same SIBH API serves the 10-minute records of the river, reservoir and
tunnel stations of SP Águas, Sabesp and SAISP. Observed records only; no
model was run.

- `pipeline/fetch_sibh_flow.py` downloads hourly means for a fixed list of 21
  station codes: the two river gauges above the reservoirs, two on the rio
  Cachoeira below Cachoeira dam, the stations at both dams and their outlet
  channels, the tunnel ends, and the Paraíba do Sul transfer. It also stores
  each station's record and its published rating curves.
- `pipeline/sibh_flow.py` builds daily means by rules fixed before any series
  was computed: a local calendar day (UTC−3), kept if at least 18 hourly means
  are valid, never filled. Two corrections were made after dry runs and before
  any result was used, and both are recorded in the script: six Sabesp codes
  serve levels in metres, not cm, and the two channel stations changed datum
  in October 2022. Output: `data/processed/sibh_flow_<id>.csv` (level, its
  datum and discharge per day). Report: `docs/sibh_flow_report.md`.

What the stations hold:

| Stations | Variable | Record |
| --- | --- | --- |
| Atibainha Montante (3E-121), Cachoeira Montante (3E-122), above the reservoirs | Stage and discharge | 2018 and 2022 onward, nearly complete |
| 3E-116, 1 km below Cachoeira dam; 3E-145 in Piracaia beside ANA 62665000 | Stage and discharge | 2010 onward (discharge only to 2019) and 2022 onward |
| Cachoeira and Atibainha dams, Tunnel 5 intake, Jacareí dam (Tunnel 7) | Reservoir level (elevation) | 2010 (Atibainha), 2015 (Cachoeira, Jacareí), 2019 (Tunnel 5 intake) onward |
| Downstream channels of both dams | Level only | 2018 (Atibainha) and 2022 (Cachoeira) onward |
| Tunnel 6 outlet (Cachoeira to Atibainha), Tunnel 5 outlet (Atibainha to Paiva Castro) | Stage and discharge | 2014–2015 onward (Tunnel 6 complete from 2020) |
| Paraíba do Sul pumping station | Level only | 2024 onward |
| Jaguari–Atibainha transfer (two codes) | Nothing | — |

Six of the codes duplicate other codes' instruments, served between May 2024
and June 2025 in metres; they agree with their twins wherever both report.

What they show:

- **SAR's inflow is noisy, the upstream gauges are not.** On rainless days
  SAR's inflow rises on 45–52% of days, with successive changes cancelling: an
  implied error of 0.5–0.8 m³/s a day. The upstream gauges rise on 18–26% of
  those days, with an implied error under 0.1 m³/s. They follow SAR's inflow
  at r = 0.88–0.94 on weekly means.
- **The Cachoeira Montante gauge reads more than SAR's inflow to the whole
  reservoir**, though it drains only part of the catchment: 1.11 times
  overall, by year 0.91 (2022), 1.22, 1.39, 1.50 (2025) and 0.98 (2026 so
  far). Its rating has changed by less than 6% since 2015. It sits 6–7 m above
  the highest lake level since 2022 (Copernicus DEM, approximate), so
  backwater from the lake is unlikely. On rainless days it reads a median of
  2.7 m³/s against SAR's 1.2. Either the gauge reads high or SAR's
  dry-weather inflow at Cachoeira is too low; which one is unresolved. Neither
  gauge's drainage area is published.
- **The Atibainha Montante gauge changed its rating in 2023 and again in
  2024**: the same stage gives 23–41% more discharge from 2024. Its flow
  before and after is not comparable without the rating history.
- **SAR's Atibainha inflow does not include the Paraíba do Sul transfer.**
  If it were the only water entering, Atibainha's balance in SAR (inflow minus
  release minus storage change) would equal the measured Tunnel 5 outflow
  minus the Tunnel 6 inflow. The two move together (r = 0.82, SAR one day
  later), but the tunnels exceed the balance by a median of 5–8 m³/s in every
  year of 2019–2022 and 2024–2026. The excess is about zero in 2015 and 2017,
  before the link opened in 2018, and in 2023. It is most likely the transfer:
  estimated here, not measured. This confirms, from measured flows, the
  runoff investigation's finding above that the transfer is not counted as
  inflow.
- **Cachoeira's balance cannot be checked**: it needs Tunnel 7, and SIBH has
  only the reservoir level there.
- **Gauge below release**: see "Data gaps" above.

**What this means for modelling.** The upstream gauges are close to the new
data that could reopen modelling: an inflow measure independent of the
reservoir balance, with far less day-to-day noise than SAR's inflow. But they
cover parts of the catchments with unknown areas, from 2018 and 2022 only;
one changed its rating, and the other reads above SAR's whole-reservoir
inflow. **No model was run.** Any run on them needs its own design, fixed in
advance.

## The gauges above the lakes on their DEM catchments, added 16 November 2026

No drainage area is published for 3E-122 (ANA 62664500, Rio da Cachoeira) or
3E-121 (ANA 62654500, Rio Atibainha); ANA's inventory confirms the codes but
leaves the field empty. `pipeline/delineate.py` now derives them from the DEM,
with the same fill and flow directions as the dam catchments. Each gauge is
snapped to the nearest stream draining at least 20 km². The rule was chosen
from the terrain alone, because the rule used for the dams would jump 540 m
downstream to a tributary junction.

| Gauge | DEM area | Other snap rule | Share of dam catchment | Nested in it | Outlet to the mapped river |
| --- | --- | --- | --- | --- | --- |
| 3E-122, Rio da Cachoeira | 295.5 km² | 301.5 km² | 74% | yes | 13 m |
| 3E-121, Rio Atibainha | 128.4 km² | 136.6 km² | 41% | yes | 21 m |

`pipeline/upstream_catchments.py` then puts each gauge on the same footing as
the operator's inflow: runoff depth against rain on its own catchment, by
year (`docs/upstream_catchments.md`). The gauge catchments return 0.33–0.49
of their rain (Atibainha, 2019–2026) and 0.22–0.33 (Cachoeira, 2022–2026). The
operator's inflow implies 0.23–0.29 and 0.16–0.25 for the whole dam
catchments. So the measured rivers above the lakes yield 1.4–2 times more water
per mm of rain than the operator's inflow implies for the whole catchment.

The open data cannot say why. The upper catchments may really yield more, the
gauge ratings may read high (3E-121's rating changed in 2023 and 2024), or the
operator's inflow may be low. Cachoeira's 2022 rain (2,323 mm on the gauge
catchment against 1,912 mm on the dam catchment) should be checked before any
use. **No model was run.**

The viewer shows all of this on the terrain: the two catchments draped in
teal, rain dots at every gauge, discharge rings at the river gauges and
tunnel outlets, and the tunnels as schematic arcs. Tunnels 6 and 5 carry
particles that follow their measured flow; Tunnel 7 and the Paraíba do Sul
transfer are grey and dashed, because no flow record is public. There is a
panel section and four chart options (catchment rain; each gauge against the
operator's inflow; the measured tunnels). Hovering over any marker says what
it is, where it comes from and its value on the replayed date.

## Flood model of Atibaia town, run 1: stopped at the data check (17 November 2026)

**Why Atibaia town.** The river does flood there. The Geological Survey of
Brazil mapped flood-risk sectors in Atibaia in 2012, and studies tie the
floods to building on the river's natural floodplain. SP Águas' telemetric
gauge in town (3E-063) has an official overflow level of 301 cm. Since
October 2014 the daily mean stage has been above it on 275 days, in 30
floods; the highest was 417 cm on 8 June 2016. That check is
`docs/flood_option_check.md`.

**The design** (`docs/model_design_flood_run1.md`, approved before any code)
was a test of flood extent, not depth. The model was driven by the measured
flow at 3E-063 and run through about 7 km of river to ANA's station above
the Salto Grande plant. Its maps of open water on open ground were to be
scored against Sentinel-1 radar at the passes taken during floods. To be
accepted it had to beat a map made from the terrain alone. The radar maps
were to be made blind, by a fixed rule, before any model map existed. A
data check came first: the radar's flooded area had to rise with the river
level.

**Changes along the way.** Each was approved by the project lead before any
model or radar map existed, and each is recorded in the design's addendum:
- **Gaps in the downstream level:** up to 3 hours are bridged, longer gaps
  drop the pass. That leaves 13 passes, at 3.24–3.59 m on the town gauge.
- **Channel width: 11 m, from OpenStreetMap.** Sentinel-2 at 10 m could not
  see the river at any of 36 transects.
- **Bank height: an unbiased least-squares fit that never rises
  downstream.** The first reading, a running minimum, sat 2.2 m low.
- **Model: LISFLOOD-FP 8.2 in place of SFINCS.** SFINCS could not carry the
  river in its 11 m channel. With only the channel open, 15 m³/s stood
  5.2–8.6 m deep on 25, 10 and 5 m grids, against about 2 m by Manning's
  equation. Calibrating roughness could not fix it. LISFLOOD-FP's subgrid
  channel passed the same test, at 2.00 m against 2.16 m.
- **LISFLOOD-FP's setup** (20 m cells, buildings, inflows), and a new tie
  for the downstream station's datum.

**What was built:**
- **Pre-run checks** (`docs/flood_run1_passes.md`): the ANADEM bare-earth
  terrain window and river profile, tributary inflow points, and a 20 m
  LISFLOOD-FP model of the reach.
- **Steady test:** steady after 10 days at 15 m³/s.
- **Channel roughness:** n = 0.020, calibrated to SP Águas' rating with an
  RMSE of 0.19 m.
- **Scoring:** a mask of 1.64 km² of open ground, and the terrain-only
  benchmark.

**The data check failed.** By the fixed rule, the radar sees 0.010–0.036 km²
of open water on the scored ground at every one of the 13 passes, 0.6–2.2%
of it. A pass needed at least 0.1 km² to be scored, so none was scored, and
by the design's rules the run stops with no model test. Nothing is shown.

**What it says, beyond the rules:**
- **The radar and the terrain disagree.** At 0.2–0.6 m above the overflow
  level, the radar sees no open water spread over the open valley floor,
  whereas the terrain says the floor should flood. The terrain-only map
  wets about 60% of the scored ground at the same passes, and the model
  already wets 0.85 km² at 15 m³/s.
- **The data cannot say why.** The floods may stay near the channel, under
  trees or in streets, all excluded from scoring. The radar may miss flooded
  grass. The 05:30 passes come after most peaks. ANADEM may put the valley
  floor too low.
- **Either way,** a flood model on ANADEM would show far more open water
  than the radar does.

The first hydraulic design, for the Cachoeira dam to Piracaia reach
(`docs/model_design_hydraulic_run1.md`), was drafted and never run: that
reach stayed in its channel throughout its record.

## Next steps

1. Send the data requests drafted in `docs/data_requests.md` (six letters in
   Portuguese with English summaries; drafted, not sent). They need a
   Brazilian partner to send or co-sign, and a native speaker's review. Part of
   what letters 1, 2, 3 and 5 ask for is already public on SIBH (see the note at
   the top of that file); check it before sending.
2. From SIBH: download the Atibaia gauge's own telemetry (62669900). Ask SP
   Águas for the drainage areas and rating histories of 3E-121 and 3E-122, and
   Sabesp for Tunnel 7 and Paraíba do Sul transfer flows (the notes at the top
   of `docs/data_requests.md` say how to trim and extend letters 1–4; the
   letters themselves are not yet rewritten).
3. Decide how to treat the two rain gauges with the wrong day (drop or shift
   those gauge-years), check Cachoeira's 2022 catchment rain, then write the
   design for any new model run. The gauges above the lakes now have DEM
   catchment areas (above), so they can be the observation such a design is
   judged against, with the rating change at 3E-121 handled explicitly.
4. Ask the operator how inflow was computed before 2000 (Atibainha looks too high).
5. Viewer: trees and clouds after the Kelani WebTwin, and checks on laptop GPUs.
6. Replace the viewer's terrain with ANADEM (bare earth). No 2 GB download
   is needed: the zone file is tiled and served with byte-range support, and
   `pipeline/fetch_anadem_window.py` reads just a window (4 MB for the flood
   reach).
7. Floods: **flood run 2 stopped at its data gate and is closed** (18 November
   2026; `docs/model_design_flood_run2.md`, design and pre-run addendum;
   `docs/flood_run2_test_b.md`, test B and the verdict; a short illustrated
   account of runs 1 and 2 in `docs/flood_modelling_summary.pdf`).
   - **What it was:** run 1's model with three fixes to its over-flooding
     (an in-bank start, the floodplain floor raised to the river's ordinary
     level, shallow hollows filled), tested blind on the evening Stripmap
     radar passes. The model would write its own velocities, and only a
     passed run would reach the viewer.
   - **The pre-run checks:**
     - **The fixes work:** the model stays in its banks at 5–15 m³/s, and
       the stage errors are unchanged.
     - **LISFLOOD-FP outputs:** it writes floodplain velocities only in
       hazard mode, and its subgrid channel velocity grid is empty. Channel
       velocity would come from the channel discharge.
     - **The radar chain:** a new one (sarsen, `envs/flood-sar.yml`)
       geolocates the evening scenes within 3 m of the mapped buildings.
   - **The gate result:** at all 21 evening passes (322–377 cm), at most
     25 pixels (0.0025 km²) of open ground read as water, against the
     1,000 pixels needed. The flooded area does not rise with the river
     (Spearman 0.08). By the design, run 2 is not accepted and nothing
     modelled is shown.
   - **The finding:** at these stages the radar, morning or evening, sees no
     broad open water on the open valley floor. The flooding the town
     records is either in grass, trees or streets, which C-band radar at
     this resolution does not show as open water, or narrow and short-lived.
   - **Test B failed** (run as information; `pipeline/flood_run2_build.py`,
     `pipeline/flood_run2_score.py`). With the corrected model, the 13
     morning floods put water at least 0.5 m deep on a median 0.20 km² of the
     open ground where the radar saw almost none (at most 0.10 km² allowed),
     and 7 floods went over 0.20 km² (at most 2 allowed). The model's level
     at the town gauge was 0.33–0.55 m *below* the record at every pass. Most
     of the deep water (57%) sits in closed hollows left in ANADEM's valley
     floor, so the ground, not the model's river, is what floods it.
   - **The verdict file** `data/processed/flood_run2_verdict.json` says
     `"passed": false` (written once; no extent test, so no stage range is
     tested). The viewer shows no modelled water.
   - **Run 1's morning radar stack is offset.** Check 4 found the
     `sentinel-1-rtc` reference used by run 1 about 43 m west of the mapped
     buildings. Run 1's morning flood maps sit that far from its scoring
     mask and model grid. That is unlikely to change run 1's outcome: its
     morning passes flagged 102–360 pixels against the 1,000 needed, and a
     43 m shift moves pixels across the mask's edges, not into being.
   - **What would make another flood run worth doing:**
     - **Ground heights for Atibaia town:** lidar or survey from the
       municipality, the state cartographic institute, or CPFL's licensing
       surveys for the Salto Grande plant. This matters more than any model
       setting.
     - **River cross-sections and rating histories** at 3E-063 (letter 2 in
       `docs/data_requests.md`), and CPFL's pond levels.
     - **A different observation of flooding:** water levels along the
       reach, flood marks, photographs, Defesa Civil records of flooded
       streets, or L-band radar, which sees water under vegetation. Neither
       C-band pass (morning or evening) can test a model here.
