# Hydraulic model, run 1: design and test, fixed before any run

Drafted 16 November 2026. **Status: draft, not approved.** No hydraulic code
has been written and nothing has been run. Once approved, nothing in this file
may be changed after any modelled water level has been compared with an
observed one.

## What run 1 is, stated plainly

- It is the pilot's first hydraulic model: LISFLOOD-FP on the Rio Cachoeira
  from Cachoeira dam to Piracaia town, about 4 km in a straight line. Its
  inputs are measured or reported flows (the dam release, and a gauge above
  the lake), not modelled inflow. It is independent of the inflow models in
  runs 1–4 and does not reopen them.
- **It cannot test flood mapping.** Since 2010 the reported release from
  Cachoeira has never exceeded 7.08 m³/s (2018–2026: 6.5 m³/s), and the
  highest daily flow at the Piracaia gauge (ANA 62665000) was 12.7 m³/s.
  Flows this small very probably stayed in the channel; bank heights are not
  known, but nothing in the record suggests otherwise. A pass would support
  in-channel water levels for releases of about 0.15–7 m³/s and nothing else.
  No flood extent or depth map may be drawn from it.
- **No surveyed cross-section is public.** Channel width and shape are
  estimated, so the model can match a gauge only by being tuned to it. The
  test that matters is whether it gets the water level right **at a place it
  was not tuned on**. The data check below shows that the only second station
  has a moving control, which makes that test hard to pass.
- For in-channel, near-steady flow, LISFLOOD-FP does what a simpler 1D
  calculation would. Its 2D floodplain capability is not exercised by this
  record. Part of the value of run 1 is building and checking the toolchain
  (bare-earth terrain → LISFLOOD-FP → viewer) on the best-gauged reach before
  any flood design.

## Data checks made before writing (observed records only, no model)

**1. The stage instruments are precise.** On steady days (reported release
unchanged that day and the three days before, and audited Cachoeira catchment
rain under 1 mm on each of those days), daily mean stage barely moves:

| Station | Years | Steady-day pairs | Median day-to-day change | 90th percentile | Days rising > 0.5 cm | Lag-1 autocorrelation of changes |
| --- | --- | --- | --- | --- | --- | --- |
| 3E-116, 1 km below the dam | 2010–2017 | 670 | 0.3 cm | 1.3 cm | 12% | 0.00 |
| 3E-116 | 2018–2026 | 758 | 0.3 cm | 1.4 cm | 12% | −0.02 |
| 3E-145, Piracaia town | 2022–2026 | 322 | 0.2 cm | 0.9 cm | 10% | 0.05 |

There is no sign of the day-to-day noise found in SAR's inflow (run 4
design). Measurement noise is not what limits a stage test here.

**2. The section at 3E-145 is stable; the one at 3E-116 is not.** Median daily
stage (m) on dry days (catchment rain under 1 mm), by year and by band of
reported release, with the number of days in brackets:

| Year | 3E-116, release 0–1.5 | 3E-116, 2–3.5 | 3E-116, 4.5–6.6 | 3E-145, 0–1.5 | 3E-145, 2–3.5 | 3E-145, 4.5–6.6 |
| --- | --- | --- | --- | --- | --- | --- |
| 2010 | 1.37 (62) | 1.91 (70) | 2.71 (25) | – | – | – |
| 2011 | 0.95 (50) | 1.77 (121) | – | – | – | – |
| 2012 | 1.16 (74) | 1.98 (31) | – | – | – | – |
| 2013 | 1.23 (118) | 1.96 (57) | – | – | – | – |
| 2014 | 1.44 (174) | 1.74 (80) | – | – | – | – |
| 2015 | 1.40 (155) | 2.36 (37) | – | – | – | – |
| 2016 | 1.64 (208) | – | – | – | – | – |
| 2017 | 1.78 (177) | 2.43 (38) | – | – | – | – |
| 2018 | 1.37 (68) | 2.27 (98) | – | – | – | – |
| 2019 | 1.35 (34) | 2.03 (34) | 2.49 (36) | – | – | – |
| 2020 | 1.26 (17) | 1.96 (30) | 2.53 (145) | – | – | – |
| 2021 | 1.33 (10) | 2.03 (17) | 2.32 (178) | – | – | – |
| 2022 | 1.45 (19) | – | 2.31 (162) | 0.83 (19) | – | 1.27 (165) |
| 2023 | 1.34 (45) | 1.66 (39) | 2.32 (94) | 0.78 (48) | 0.94 (40) | 1.21 (100) |
| 2024 | 1.37 (29) | 1.76 (24) | 2.21 (148) | 0.79 (23) | 0.96 (24) | 1.22 (34) |
| 2025 | 1.34 (44) | 1.71 (26) | 2.24 (121) | 0.79 (44) | 1.03 (35) | 1.22 (126) |
| 2026 | 1.23 (43) | 1.64 (14) | 2.22 (115) | 0.76 (43) | 0.98 (14) | 1.21 (117) |

- At 3E-145 the stage in each band varies by at most 9 cm between years from
  2022 to 2026 (6 cm in the highest band). The rise from the lowest to the
  highest band is 0.43–0.45 m every year.
- At 3E-116 the stage for the same release moves by tens of centimetres
  between years (2–3.5 m³/s band: 1.64–2.43 m). Its 23 published rating
  curves (2001–2016) agree: the zero-flow stage of their lowest segment moved
  from 0.0 m (2001–2008) to 1.0 m (2016). No curve has been published since
  2016, and SIBH's discharge for it stops in January 2020. Within each year of
  2019–2026, 3E-116 rises 0.84–1.27 m from the lowest to the highest band,
  two to three times as much as 3E-145 for the same release. That points to a local control, possibly a weir or other structure
  at the water intake, which a terrain-based channel will not contain.

**Disclosure.** The second table shows the stage response at both test
stations. Neither test below is blind to it.

## Reach, grid and software

- **Domain:** a corridor within 500 m of the OpenStreetMap river centreline,
  from the dam outlet cell (DEM delineation outlet, −23.0496, −46.3246) to
  1.5 km downstream of 3E-145. Grid: 30 m, reprojected to SIRGAS 2000 / UTM
  23S (EPSG:31983).
- **Terrain: ANADEM (bare earth) only.** Copernicus GLO-30 is a surface model;
  the riparian forest along this river would put the "banks" metres too high.
  Without ANADEM there is no run 1.
- **Software:** LISFLOOD-FP 8.2, the official release, built from source on
  Windows with Visual Studio and CMake. Its Zenodo record (cited by others as
  10.5281/zenodo.13121102) is to be confirmed as official before use. If it
  cannot be confirmed, use 8.0 (10.5281/zenodo.4073011). The archive's
  SHA-256 goes into `data/raw/manifest.jsonl`. The 8.3 release on Zenodo is
  not used: it is a separate effort and builds only on Linux and macOS.
  Solver: acceleration (local inertial) with the subgrid channel, on CPU.
  Licence: GPL (v2 on Zenodo, v3 on the project pages); the model is run, not
  redistributed.
- **Pipeline:** standard-library Python writes the inputs, runs
  `lisflood.exe` as a subprocess and reads the outputs, as in the rest of
  `pipeline/`. The binary and its outputs are not committed.

## Inputs, fixed here

| Input | Source | Rule |
| --- | --- | --- |
| Upstream flow | SAR, Cachoeira daily release | Constant through each day, entered at the dam outlet cell. Reported, not measured (data request letter 1, item 4) |
| Lateral inflow | Area between the dam outlet and each station, from `delineate.py` (snap rule: nearest cell draining at least 20 km², as for the gauges above the lakes) | Same-day specific discharge at 3E-122 (Cachoeira Montante, 295.5 km²) times that area, entered at the largest tributary junction above each station. About 33 km² reach Piracaia (DEM: 397.0 km² at the dam, 430.4 km² at ANA 62665000) |
| Channel width | OSM river polygons where mapped, otherwise measured on the August 2024 Sentinel-2 composite already used by the viewer | Measured every 250 m and at both stations before any run; linear in between. Listed in the addendum |
| Channel bed | ANADEM elevation along the OSM centreline, forced to fall monotonically downstream, minus a bank-full depth | Bank-full depth: the smallest multiple of 0.25 m that keeps a steady 13 m³/s (just above the highest daily flow on record since 2010) inside the channel at every cell, with n = 0.100 (the roughest value tried). The same depth is used for every n. In a rectangular channel it sets only when water would leave the channel, not the in-channel rise in level |
| Channel roughness | Manning's n, one value for the reach | **The only calibrated parameter** |
| Floodplain roughness | ESA WorldCover classes, fixed table in the addendum | Not calibrated; expected to have no effect in-channel |
| Downstream boundary | Free outflow at the ANADEM slope of the last 1 km | Must pass pre-run check 4 |

Structures (weirs, bridges, the intake) are not represented in run 1.

## How the model is run: quasi-steady lookup

Travel time through about 6 km of channel at in-channel velocities is a few
hours, and the release is reported only as a daily value. So for each value of
n, the model is run to steady state at 30 flows from 0.1 to 15 m³/s
(log-spaced). That gives a modelled water level against local flow at each
station. Daily modelled stage is read from this table at the day's local flow
(release at 3E-116; release plus lateral inflow at 3E-145). Pre-run check 5
confirms this shortcut.

## Calibration and tests, fixed here

Scored on daily means. Only days with valid stage and a reported release are
used. No day is dropped for any other reason. Each station's stage is in its
own gauge datum, so an offset (observed minus modelled, median) is fitted.

**Calibration (3E-145, 2022-01-01 to 2023-12-31).** For n from 0.020 to
0.100 in steps of 0.005, fit the 3E-145 offset and compute the mean absolute
error (MAE). Pick the n with the lowest MAE. That n and that offset are then
frozen. The few 3E-145 days in 2018 and 2021 are not used.

**Test 1: temporal, at 3E-145 (2024-01-01 to the end of the record at run
time).** Same station, unseen years, frozen offset. All four must hold:

1. MAE at most 6 cm.
2. Mean error within ±3 cm (the frozen offset still fits).
3. Response ratio between 0.8 and 1.25. The response is the median stage on
   dry days with release 4.5–6.6 m³/s minus that with release 0–1.5 m³/s,
   modelled divided by observed.
4. MAE at most 1.25 times that of a **benchmark curve**:
   stage = h₀ + c·Q^b at 3E-145, with Q the same local flow the model uses,
   fitted by least squares on the calibration days. At a gauge, a fitted curve
   is the reference. The hydraulic model need not beat it there, but must not
   be much worse, because its value is meant to be away from the gauges.

**Test 2: spatial, at 3E-116 (2019–2026).** The model is not tuned here at
all. Because the control at 3E-116 moves between years, one offset is fitted
per year (the median of that year's differences). That removes the level
shift and leaves only the response to flow, which is what the model claims to
know. Years count only if both release bands have at least 10 dry days
(currently all eight). Both must hold:

1. In at least six of the eight years, the response ratio (as in test 1) is
   between 0.67 and 1.5.
2. MAE over all days, after the yearly offsets, at most 10 cm.

**Tolerances.** The numbers are judgements, set from the data checks above.
The instruments contribute about 1 cm. A reported release that is off by a
quarter of a m³/s moves 3E-145 by about 2 cm (0.44 m over roughly 5 m³/s). An
error of 100% in a dry-weather lateral inflow of about 0.3 m³/s moves it by
about 3 cm. Test 2 is wider because 3E-116 responds two to three times more
strongly to flow.

**Reported, not scored:** the same scores with lateral inflow ×0 and ×2; the
3E-145 scores on the 108 days of 2022 on which the README notes that 3E-145
read short of the release; modelled against SIBH discharge at 3E-145 (its
rating is unpublished); and the n chosen if 3E-116 is used for calibration
instead, to show how far the two stations disagree.

## Pre-run checks (no comparison with observed stage)

Recorded in an addendum to this file and committed before any modelled stage
is compared with an observed one. Modelled output may be computed for checks
4 and 5.

1. ANADEM downloaded, logged in the manifest, clipped to the corridor; the
   centreline profile plotted.
2. Weirs, bridges and intake structures within 300 m of either station or
   along the reach, from OSM and Sentinel-2, listed. Run 1 does not model
   them; finding one at 3E-116 does not change the test.
3. LISFLOOD-FP version confirmed, built and hashed; the subgrid channel
   keywords confirmed from the 8.2 manual.
4. Downstream boundary: changing its slope by ±50% must move steady stage at
   3E-145 by under 2 cm at every one of the 30 flows. If not, extend the
   domain by 1 km and repeat.
5. Quasi-steady shortcut: one unsteady run of 2023 at n = 0.040, driven by
   the daily release and lateral inflow. Its daily mean stage at both
   stations must be within 1 cm of the lookup on 95% of days.
6. Lateral areas at both stations and the tributary junctions, and the
   channel width table, listed.

If check 3, 4 or 5 cannot be met, run 1 stops and a revised design is needed.

## Outcome rules

- **Tests 1 and 2 both pass.** Accepted for daily in-channel water level
  along the reach, for the range of local flow on the test days, given the
  reported release. The viewer may show the modelled water level and depth
  along the river channel for the replayed date. It is labelled **"modelled:
  hydraulic run 1, in-channel only, depends on reported release; channel
  shape estimated, not surveyed"**. Nothing is shown on days when the local
  flow is outside the tested range, and no floodplain water is ever drawn.
  `tests/test_pipeline.py` is extended so that no hydraulic layer reaches the
  viewer without an accepted run.
- **Test 1 passes and test 2 fails.** Not accepted. The model has only learned
  the curve at one gauge, which a fitted rating curve already provides.
  Nothing is shown. The toolchain is kept for a later design with surveyed
  cross-sections.
- **Test 1 fails.** Not accepted. Nothing is shown. No re-tuning: a revised
  model is a new run with its own design.

## Expectation, written before the run

- Test 1 should pass. The 3E-145 section is stable, flow stays in the channel
  and only one parameter is fitted. The likeliest failure is criterion 4, if
  the modelled curve cannot bend like the real one.
- Test 2 is likely to fail. 3E-116 responds two to three times more strongly
  than 3E-145 to the same release, which suggests a local control that a
  channel estimated from 30 m terrain and imagery will not contain, unless the
  measured width there happens to be very narrow.

## Should run 1 go ahead?

If the expectation holds, the outcome is "test 1 passes, test 2 fails, not
accepted". That leaves a built and checked toolchain, but no model claim.
There are three honest options:

- **A. Run it as designed**, mainly to build and check the toolchain on the
  best-gauged reach, knowing acceptance is unlikely.
- **B. Hold it until surveyed cross-sections arrive.** Data request letter 2
  asks SP Águas for the yearly cross-sections at its gauges. With measured
  shapes at 3E-116 and 3E-145, test 2 becomes a real test of roughness alone,
  and that would be a new design.
- **C. Design a flood run instead, for the Rio Atibaia through Atibaia town.**
  SP Águas' gauge there (3E-063) has an official overflow level of 301 cm,
  exceeded in many floods since 2010. That is a test of floodplain mapping,
  the job LISFLOOD-FP is built for. Its data were checked after this design
  was drafted: `docs/flood_option_check.md`. (An earlier draft cited ANA's
  110 m³/s on 15 January 2021. That value is spurious: the river carried
  about 30 m³/s that day.)

The choice is the project lead's. A and B are not exclusive.

## What this design does not fix

- The release is the operator's reported value, not a measured outflow.
- Lateral inflow is scaled from a gauge that reads above the operator's
  inflow (README, "River, dam and tunnel stations").
- Channel width at 10 m pixels is uncertain for a river this narrow.
- Uncertainty is not propagated. The only spread reported comes from the
  lateral-inflow runs at ×0 and ×2.
