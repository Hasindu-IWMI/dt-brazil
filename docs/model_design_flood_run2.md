# Flood model, run 2 (Atibaia town, LISFLOOD-FP): design and test, fixed before any run

Drafted 18 November 2026. **Status: approved by the project lead on
18 November 2026, as drafted** (each decision at the end takes the option
written first or marked recommended; "Approval" below lists them).
Nothing has been built or run for run 2. **No evening (Stripmap) radar scene
has been downloaded or looked at**, so the main test below can still be
blind. Once approved, the only additions allowed are the pre-run addendum,
and nothing in this file may be changed after any modelled flood map has been
compared with an observed one.

This design is written **knowing run 1's result**: at the 13 morning passes
the radar found almost no open water on the valley floor
(`docs/model_design_flood_run1.md`, "Observed flood maps and the data gate").
The morning passes therefore cannot be a blind test. They are used below as
a known-answer check (test B). The blind test (test A) uses the evening
passes, which nobody has looked at.

## What run 2 is, stated plainly

- The same reach, model and inputs as run 1's approved LISFLOOD-FP setup:
  the Rio Atibaia from 1.5 km above SP Águas' gauge 3E-063 to the Salto
  Grande station (ANA 62671200), 8.7 km², driven by measured hourly flow at
  the town gauge. Everything run 1's addendum approved carries over unless
  this file changes it.
- **Three changes to the model**, each meant to stop the over-flooding found
  in run 1, each fixed here from evidence that uses no radar beyond run 1's
  published result (section "Why run 1 over-flooded").
- **A new blind test** on the evening Stripmap passes, with its data gate
  written before any evening scene is read.
- **A known-answer check** that the model does not flood the open ground
  where the morning radar saw no water.
- **The model writes its own velocities**, and the run ends with a verdict
  file that decides, by itself, whether the viewer may show the water.
- **The claim it seeks:** given the measured flow at the town gauge, the model
  maps which open ground is under water better than a terrain-only map, and
  does not flood open ground that the radar saw dry.
- **Not claimed, even on a pass:** depths, velocities, flooding of streets,
  buildings or woodland, timing, floods outside the tested range, or any
  forecast. Depth and velocity are drawn in the viewer only as untested
  detail of a tested extent, if you approve that (decision 6).

## Why run 1 over-flooded (data in hand; no new radar)

All numbers below come from run 1's own model folders, the hourly gauge
records, ANADEM and WorldCover. None comes from a radar image.

1. **The 15 m³/s steady test that showed 0.85 km² wet was not the calibrated
   model.** It used channel n = 0.035, before calibration. At 15 m³/s that n
   puts the gauge 0.33 m above the rating, over the bank, and 107 channel
   cells overtopped. After 10 days 0.78 km² of floodplain held water at least
   10 cm deep. With the calibrated n = 0.020, the same flows (5, 10 and
   15 m³/s) stay in the channel: no channel cell overtops, and only
   0.019–0.027 km² of floodplain is wet. Most of that is the boundary strip
   at the station. (The viewer's TEST RENDER, and the README's
   "1.02 km² wet", come from the uncalibrated run too.)
2. **Run 1's start rule would have begun most floods already flooding.** Each
   run was to start "72 hours before the pass, from a steady state at that
   hour's flows". At **10 of the 13 morning passes the river was already over
   the overflow level (301 cm) 72 hours before**. A steady state at an
   overbank flow is a flood that never ends: it fills every hollow it can
   reach, whatever the flood's real volume.
3. **ANADEM puts much of the valley floor below the river.** On the model's
   20 m grid, 2.34 km² of the 8.47 km² floodplain lies below the bank of the
   nearest channel cell. **1.74 km² lies below the river's ordinary level**
   (the bank minus 0.82 m: the bed is 2.11 m below the bank, and the median
   depth at 3E-063 is 1.29 m), by a median 1.1 m (90th percentile 2.2 m).
   Ground lower than the river beside it would be waterlogged or open water.
   WorldCover 2021 classes that ground as 43% grassland, 42% tree cover, 8%
   built-up, 3% water and 0% wetland: dry land. So ANADEM's floor is too low
   there, or the fitted bank too high, by about a metre.
4. **Water that enters a hollow never leaves.** With the channel cells as
   outlets at bank level and the domain edge as the other outlet, 456 closed
   depressions cover 2.74 km² and could hold 3.68 Mm³. The model exchanges
   water with the subgrid channel over the bank. Water below the bank in a
   hollow therefore stays until the run ends. In reality, ditches and
   streams too small for a 30 m terrain model drain it.
5. **The terrain-only benchmark floods about 60% of the scored ground** at
   every pass, for the same reasons as points 3 and 4.

## The three changes, fixed now

**Change 1: in-bank, dry-floodplain start (replaces "steady state 72 hours
before the pass").**
- Each event starts at the **last hour before the pass at which 3E-063 stood
  below the overflow level (301 cm)**, searched back up to 14 days. Every
  candidate pass, morning or evening, has such an hour, 0.4 to 11.3 days
  before it.
- **Stage 1:** a channel-only run reaches a steady state at that hour's flows.
  The floodplain is closed (all floodplain cells raised 20 m), and the run
  lasts 10 days, as run 1 found necessary.
- **Stage 2:** the full model starts from stage 1's channel depths, with the
  floodplain dry (LISFLOOD-FP `startfile`; confirmed in pre-run check 2). It
  runs with hourly inflows and downstream levels to the pass.
- Mapped permanent water (WorldCover classes 80 and 90, and OSM water
  polygons inside the domain; 0.06 km² in all) starts full to its spill level,
  because it holds water before any flood.
- **Why:** a flood's water on the floodplain is limited by the volume that
  actually overtopped the bank during that flood. The steady overbank start
  gave the floodplain unlimited volume.

**Change 2: the floodplain floor no lower than the river's ordinary level.**
- Floodplain cells not mapped as water whose ANADEM ground lies below the
  ordinary river level at their nearest channel cell (fitted bank − 0.82 m)
  are raised to that level.
- Nearest means the closest channel cell along the domain's cells (4-connected).
- This raises about 1.74 km², by a median 1.1 m.
- **Why:** point 3 above. This is the smallest correction that makes the
  terrain agree with the land cover. It does not claim to know the true
  floor, which may be higher still.

**Change 3: hollows drain, within the terrain's own error.**
- After change 2, closed depressions in the floodplain are filled to their
  spill level, but only those whose deepest point is no more than 1.5 m below
  it. The outlets are the channel cells (at bank level) and the domain edge.
- Deeper depressions are kept and listed in the addendum. Mapped water is not
  filled.
- **Why 1.5 m:** it is ANADEM's own scatter on this river, measured in run 1.
  Raw bank heights lie −1.66 to +1.24 m around the fitted bank (10th to 90th
  percentile). A hollow no deeper than that cannot be told from noise.
  Filling it lets water that overtops the bank flow on and back to the
  channel, as the unresolved ditches would.
- On run 1's ground, before change 2, depressions no deeper than 1.5 m cover
  0.54 km²; deeper ones cover 2.20 km². Change 2 makes many of those
  shallower. The areas after both changes are reported in pre-run check 3.

**Kept from run 1:** channel n = 0.020 from the calibration (the rule picked
it; it is not re-tuned). The calibration's in-bank stage errors must be
unchanged within 2 cm after changes 2 and 3 (pre-run check 3), since they
touch only the floodplain.

**Expected effect, written before any run:**
- Change 1 removes the endless-flood start.
- Changes 2 and 3 make the floodplain near the river no lower than the bank,
  except in deep hollows. Water that overtops the bank then spreads thinly
  and drains back when the river falls.
- At the flood peak the extent may still be large: the scored passes stand
  0.2–0.8 m above the bank at the gauge. These changes cannot make ANADEM
  right. They remove three ways the model created water the river never
  delivered.

## Reach, grid, inputs (unchanged from run 1's approved LISFLOOD-FP setup)

| Item | Run 2 |
| --- | --- |
| Model | LISFLOOD-FP 8.2, Docker image `atibaia/lisflood-fp:8.2` (already built and hashed), acceleration solver with subgrid channel, CPU |
| Grid | 20 m, EPSG:31983, 267 × 228, the same 8.7 km² domain |
| Ground | ANADEM bilinear to 20 m, then changes 2 and 3; buildings: cells at least half covered by footprints raised 10 m (2,559 cells) |
| Channel | Run 1's 566-cell path, width 11 m (OSM tag), isotonic bank, bed = bank − 2.11 m, n = 0.020 |
| Floodplain roughness | Run 1's WorldCover table |
| Inflow | Hourly discharge at 3E-063 (SP Águas rating), `QVAR` at the upstream channel cell |
| Tributaries | Run 1's four points and its scaling of measured flow (local specific discharge above the town × area) |
| Downstream | Hourly level at 62671200 through run 1's approved datum tie (station zero 738.54 m), `HVAR` on the 28 cells across the valley |
| Rain on the grid | Off (as run 1) |
| Outputs | `saveint 3600`: depth (`.wd`, `.wdfp`) and the model's velocities (`voutput`: `.Vx`, `.Vy`) every hour from 24 hours before each pass to 1 hour after, plus the maxima; mass file checked every run |

**Gaps (run 1's approved rule, now over the whole event window):** a gap of
up to 3 consecutive hours in the 62671200 level, or in the 3E-063 flow, is
bridged linearly for the boundary input only; a pass with a longer gap is
not scored. Over the change-1 windows, the 13 morning passes all qualify
(longest gap 1 hour). Three evening candidates do not: 11 June 2016 (163
hours missing), 30 December 2022 (12 hours) and **4 February 2023 (46 hours;
at 377 cm, joint highest of all the candidates)** (decision 5).

## Observed flood maps from the evening passes, fixed before any run

Made and committed, with the gate result, before any run 2 event is
simulated.

**Passes.**
- Every Sentinel-1 Stripmap pass, ascending (21:35–21:44 UTC, 18:35–18:44
  local), from 2 days before to 6 days after each flood peak since October
  2014, taken while 3E-063 stood at least 0.2 m above the overflow level
  (321 cm or more) in the hour of the pass.
- Each needs complete event windows (above) and at least three dry
  references.
- The catalogue search in pre-run check 1 makes the list. The best pass per
  flood in `docs/flood_option_check.md` section 2 gives the expected
  candidates:

| Pass (UTC) | Polarisation | Stage (cm) | Flow (m³/s) | Event start (change 1) | Longest 62671200 gap | Expected |
| --- | --- | --- | --- | --- | --- | --- |
| 2016-01-19 21:35 | HH/HV | 341 | 24.8 | 4.5 days before | 0 h | candidate |
| 2016-03-12 21:43 | VV/VH | 350 | 27.8 | 11.3 days | 1 h | candidate |
| 2016-06-11 21:35 | HH/HV | 328 | 20.8 | 6.8 days | 163 h | not scored |
| 2017-01-12 21:43 | VV/VH | 343 | 25.4 | 1.8 days | 0 h | candidate |
| 2017-01-24 21:43 | VV/VH | 361 | 31.6 | 8.2 days | 0 h | candidate |
| 2018-02-01 21:35 | HH/HV | 340 | 25.3 | 2.5 days | 0 h | candidate |
| 2019-03-04 21:35 | HH/HV | 345 | 26.3 | 3.2 days | 0 h | candidate |
| 2020-02-27 21:35 | HH/HV | 360 | 31.0 | 3.2 days | 1 h | candidate |
| 2021-01-15 21:43 | VV/VH | 351 | 28.3 | 3.0 days | 0 h | candidate |
| 2021-03-10 21:44 | VV/VH | 323 | 19.4 | 3.0 days | 0 h | candidate |
| 2022-02-04 21:36 | HH/HV | 330 | 21.6 | 5.5 days | 0 h | candidate |
| 2022-12-30 21:44 | VV/VH | 360 | 31.1 | 2.4 days | 12 h | not scored |
| 2023-02-04 21:44 | VV/VH | 377 | 37.2 | 2.9 days | 46 h | not scored |
| 2025-02-05 21:44 | VV/VH | 334 | 20.9 | 4.7 days | 0 h | candidate |
| 2026-02-01 21:35 | HH/HV | 331 | 20.3 | 2.8 days | 0 h | candidate |
| 2026-02-12 21:44 | VV/VH | 377 | 34.6 | 4.9 days | 0 h | candidate |
| 2026-03-14 21:43 | VV/VH | 356 | 27.5 | 2.6 days | 0 h | candidate |

That is 14 candidates, 323–377 cm: 6 in HH/HV (the 21:35 orbit) and 8 in
VV/VH (the 21:43 orbit). Other qualifying passes within the windows will be
added by the rule, not by choice.

**Images and processing.**
- **Source:** Planetary Computer `sentinel-1-grd`, the Stripmap GRD scenes.
  These are not in `sentinel-1-rtc`, so run 2 must process them itself. Only
  windows around the domain are read, by byte range.
- **Processing, fixed here:**
  1. Calibrate to sigma-nought with each scene's own calibration table.
  2. Remove thermal noise with its noise table.
  3. Terrain-correct with GLO-30 (ellipsoidal heights).
  4. Flatten the radiometry to gamma-nought, so the values compare with run
     1's `sentinel-1-rtc` scenes.
  5. Resample to run 1's scoring grid (EPSG:32723, 10 m, 521 × 443).
- **Tool:** sarsen (open source, Apache-2.0) in a new pinned conda
  environment; ESA SNAP 10 only if sarsen cannot read these scenes
  (decision 3).
- **Channel:** the co-polarised channel only (HH for the 21:35 orbit, VV for
  the 21:43 orbit). The two groups are mapped and reported separately, and
  scored together.

**Rules for an observed map.**
- **Reference (dry) image:** the median of the dry passes of the same
  relative orbit and polarisation within 60 days either side, with 3E-063
  below 240 cm at the pass. Run 1's rule, capped at the 8 nearest in time to
  bound the downloads. At least three are required.
- **Flooded pixel:** run 1's rule, unchanged. Gamma-nought at the pass at
  least 3 dB below the reference **and** below −15 dB.
- **New: patch rule.** A flooded pixel counts only if it belongs to a group of
  at least 4 connected flooded pixels (400 m², 4-connected).
  - **Why:** run 1 found most flagged pixels were isolated noise spread over
    the whole grid, hillsides included.
  - It is fixed here, before any evening scene is read, and applies to the
    evening maps only.
  - Test B uses run 1's committed morning maps as they are.
- **Scoring mask:** run 1's mask (1.64 km² of open ground), minus mapped
  permanent water (WorldCover 80 and 90, and OSM water polygons). It does not
  depend on changes 2 and 3.
- **Too small to score:** fewer than 1,000 flooded pixels (0.1 km²) on the
  mask. Reported, not scored. This is run 1's rule.

**Data gate, fixed now (no model involved):**
- **G1:** at least **4** evening passes reach the 1,000-pixel minimum.
- **G2:** across all evening passes with radar data, the flooded pixel
  count rises with the stage at the pass (Spearman correlation at least 0.5).

If either fails, **there is no extent test and run 2 is not accepted**.
- Test B is still run and reported, as information.
- The evening maps are reported, not shown.
- The finding becomes that, morning or evening, the radar sees no broad open
  water on the open valley floor at these stages.

## Test A (blind): extent at the evening passes

Each modelled map is the water at the hourly output nearest the pass, central
run, on the 10 m scoring grid. A cell counts as wet if the modelled depth is
over 10 cm (run 1's rule).

- **Critical success index (CSI)** per scored pass, on the scoring mask.
- **Terrain-only benchmark**, made before any model run:
  - **Ground:** the same corrected ground as the model (changes 2 and 3), so
    that the comparison tests the hydraulics, not the terrain edits.
  - **Wet cells:** run 1's height-above-river rule, stage − 1.50 m.
  - **Connected:** only cells joined to the channel through cells that also
    pass the rule (4-connected).
  - Run 1's unconnected benchmark is reported beside it.

**Test A passes only if all three hold (run 1's thresholds, unchanged):**

1. Median CSI over the scored passes at least **0.45**.
2. The model beats the benchmark: median CSI at least **0.05** higher, and a
   higher CSI on at least **two-thirds** of the scored passes.
3. Median ratio of modelled to observed flooded area between **0.67 and
   1.5**.

## Test B (known answer): no false flooding at the 13 morning passes

**Not blind:** the observed result is already known (102–360 flagged pixels,
0.010–0.036 km², at every pass). What is not known is the model's result, and
no setting is tuned to it.

- The 13 passes scored in run 1, simulated by the event rules above.
- **Deep water** is modelled water at least **0.5 m** deep on the run 2
  scoring mask, at the hourly output nearest the pass. Water that deep stands
  above pasture, so the radar would see it as open water. Shallower water in
  grass may brighten instead, and is not counted against the model.
- **Test B passes if** the median deep-water area is at most **0.10 km²**
  (the size below which run 1 could not score a pass), **and** no more than
  **2** of the 13 passes exceed **0.20 km²**.
- **Reported:** the area wet over 10 cm, and the CSI against run 1's
  committed morning maps.

## Acceptance

**Accepted only if** the gate passes, test A passes and test B passes.
Nothing is re-tuned after a result: a revised model is a new run.

## Reported, not scored

- **Variations,** one at a time, on every scored event: each of changes 1, 2
  and 3 switched off (to show what each did); inflow × 0.8 and × 1.25;
  tributaries × 0.5 and × 2; downstream level ± 0.5 m; channel n ± 0.010;
  width 7 m and 17 m (approved in run 1); buildings removed.
- **The fraction of variations in which each cell is wet,** as an uncertainty
  band.
- **The flow at which the model first leaves the channel at 3E-063,**
  against the observed 20–24 m³/s.
- **Cost:** 15 runs × about 27 events, each a 10-day channel warm-up plus up
  to 11 days of event. About 400 runs, or roughly a day of computing on this
  machine; the estimate is rough.

## Velocities, the verdict file and the viewer

- **Velocities:** the model's own output (`voutput`).
  - Pre-run check 2 confirms what LISFLOOD-FP 8.2 writes: grid (cell faces
    or centres), units, and what it writes in channel cells.
  - Where the subgrid channel carries the flow, the channel velocity is the
    channel discharge ÷ (11 m × channel depth), along the channel path. That
    rule is stated now, in case the floodplain velocity grid does not cover
    the channel.
  - No velocity is derived from the water surface, as the display test did.
- **Verdict file:** `data/processed/flood_run2_verdict.json`, written once by
  the scoring script and never edited:
  `{"run": "flood run 2", "design": "docs/model_design_flood_run2.md",
  "passed": true|false, "gate": {...}, "test_a": {...}, "test_b": {...},
  "tested_stage_cm": [min, max], "decided_utc": ...}`. `passed` is true only
  if the acceptance rule holds.
- **Publishing:** `pipeline/flood_water_viewer.py` already refuses to write
  `web/public/data/flood_water.json` unless the verdict says
  `"passed": true`, and the viewer shows a published file only if it says
  `accepted: true`. `tests/test_pipeline.py` already checks both.

**If accepted:**
- **Which floods:** every flood since 2015 whose highest stage at 3E-063
  lies within the tested range, simulated by the same event rules, as the
  scored events were.
- **Frames:** one per local day (UTC−3), dated as the viewer's dates. Each
  shows the water at that day's highest-stage hour. Days above the tested
  range are not shown. 8 June 2016 (about 420 cm) lies outside any range
  these passes can test.
- **Label:** "modelled: flood run 2; extent tested on open ground; depth and
  velocity not tested; 30 m ground heights; tributary inflow estimated".
- **Untested land:** built-up land and tree cover (outside the scoring mask)
  are drawn paler, as not tested.

**If not accepted:**
- Nothing modelled is shown.
- If the gate passed, the evening radar maps are data and may be shown on
  their dates, labelled "derived from Sentinel-1: open water on open ground"
  (run 1's rule).

## Pre-run checks (no comparison with any observed flood map)

Recorded in an addendum to this file and committed before any event is
simulated.

1. **Pass list.** Catalogue search for the Stripmap scenes, using metadata
   only. Write the table (passes, polarisation, relative orbit, stage, flow,
   event start, gaps, references) to `docs/flood_run2_passes.md`.
2. **LISFLOOD-FP checks.** Run each on run 1's synthetic smoke channel.
   - `voutput` writes `.Vx` and `.Vy` hourly. Record their grid, units and
     values in channel cells. On the synthetic 11 m channel at 15 m³/s, the
     mean velocity must come out within 20% of Q ÷ (width × depth).
   - `startfile` restores the subgrid channel's depth.
3. **Terrain changes.** Apply changes 2 and 3 to the 20 m ground.
   - Report the area raised, the depressions filled, and the deep
     depressions kept.
   - Re-run the steady tests at 5, 10 and 15 m³/s with n = 0.020. The stage
     errors at 3E-063 must be within 2 cm of the calibration's, and the
     floodplain must hold at most 0.05 km² of water over 10 cm (in-bank by
     the rating). If either fails, stop: the design needs revising.
4. **Processing chain, dry scenes only.** Process one dry scene from each
   evening orbit.
   - Its geolocation against the orbit-53 `sentinel-1-rtc` dry median must
     be within 10 m, by cross-correlation on the scoring grid.
   - The median gamma-nought on the scored ground must be within 2 dB of run
     1's −7 to −9 dB.
   - The reservoirs (open water) must read below −15 dB.
   - If any of these fails, fix the processing, or fall back to SNAP, before
     any flood scene is read.
5. **Event windows.** Fix the scored list by the gap rule.
6. **Observed maps and the gate.** Make the evening maps, run the gate and
   commit both. No model event run exists at this point.

## New or changed scripts (to be written after approval)

Run 1's scripts are frozen and are not edited.

- `pipeline/fetch_s1_sm_passes.py` (new): the Stripmap catalogue search and
  the pass table.
- `pipeline/flood_sm_maps.py` (new, `atibaia-sar` environment): reads the
  windows, calibrates, terrain-corrects, builds references, applies the flood
  and patch rules, runs the gate. Writes `data/processed/flood_run2_observed.*`
  and `docs/flood_run2_observed.png`.
- `pipeline/flood_run2_terrain.py` (new): changes 2 and 3, the run 2 scoring
  mask and the connected benchmark.
- `pipeline/flood_run2_build.py` (new): event models with the two-stage
  start, central run and variations, in the existing Docker image.
- `pipeline/flood_run2_score.py` (new): tests A and B, the variations, the
  report, and the verdict file.
- `pipeline/flood_water_viewer.py` (changed):
  - read `.Vx`/`.Vy` on cell faces and average them to centres;
  - take the channel velocity by the rule above;
  - store only wet cells, so the published file stays under about 10 MB;
  - add a per-cell "tested" flag from the scoring mask;
  - date frames by local day.
- `web/src/scene/floodwater.js` (changed): draw untested cells paler; take
  the label from the file.
- `tests/test_pipeline.py` (changed):
  - the verdict file's fields;
  - published frames only within `tested_stage_cm`;
  - the verdict is never edited after it is written (its hash is in the
    report).

## Downloads that need your approval

| What | Source | Size (approx.) | Why |
| --- | --- | --- | --- |
| STAC catalogue entries for Stripmap GRD scenes over the domain, October 2014 to November 2026 | Microsoft Planetary Computer, `sentinel-1-grd` | 2–5 MB | Pass list and references |
| Co-polarised measurement windows (HH or VV) of each scored evening pass and up to 8 dry references, about 14 × 9 ≈ 125 scenes, read by byte range from the GRD COGs | Planetary Computer, `sentinel-1-grd` (Copernicus Sentinel data, free and open) | 0.3–0.7 GB (2–5 MB per window); cached outside git | The observed maps |
| Each scene's annotation, calibration and noise XML | Same | 1–4 MB per scene, 0.2–0.5 GB | Calibration, noise removal, orbit for geocoding |
| Copernicus GLO-30 tile `Copernicus_DSM_COG_10_S24_00_W047_00_DEM.tif`, window only | AWS open bucket `copernicus-dem-30m` | About 5 MB read (tile about 40 MB) | Terrain correction |
| EGM2008 geoid grid `us_nga_egm08_25.tif` | PROJ data CDN (cdn.proj.org) | About 80 MB | GLO-30 heights to the ellipsoid |
| Conda environment `atibaia-sar` (sarsen, xarray-sentinel, rasterio, dask; pinned and locked) | conda-forge / PyPI | 0.8–1.5 GB on disk | Stripmap processing |
| Only if check 4 needs them: precise orbit files (`AUX_POEORB`), one per scene | Copernicus Data Space Ecosystem | About 4.5 MB each, at most about 0.6 GB | Geolocation |
| Only if sarsen cannot read these scenes: ESA SNAP 10 | ESA STEP | About 1.2 GB | Fallback processor |

**Nothing hydrological needs downloading:**
- the hourly SIBH records for 3E-063 and 62671200 are in hand to
  17 November 2026;
- LISFLOOD-FP 8.2 is built;
- ANADEM, WorldCover, the footprints and the OSM river are in hand.

## What remains uncertain

- **Ground heights.** ANADEM is a 30 m bare-earth model with errors of metres.
  - Change 2 corrects only its most implausible part, and the true floor may
    be higher.
  - The viewer's terrain is GLO-30, a surface model with trees and roofs, so
    modelled water drawn on it will not match the ground the model used.
- **Channel.**
  - The 11 m width is a mapper's single value for the whole reach.
  - n = 0.020 is at the low edge of its range and is an effective value: it
    makes up for the staircase path, which is 28% longer than the river.
  - The model's stage–discharge curve is flatter than the rating (0.68 m
    against 1.14 m from 5 to 15 m³/s), and no single n fixes that.
- **Downstream level.** The datum tie ignores the plant's pond, so the
  boundary is probably too low. The ± 0.5 m variation brackets it, and the
  pond and crest are still unknown.
- **Flows.**
  - The tributaries (about 190 km²) are scaled from measured flow, not
    measured.
  - Discharge above the overflow level rests on a rating segment unchanged
    since 2002, probably extrapolated.
- **The radar sees open water on open ground only.**
  - Streets, built-up land and woodland, where much of the town's flooding
    may be, are not tested at all.
  - Flooded grass brightens and is missed.
  - Change detection and the −15 dB threshold have not been checked on HH
    before. The two polarisation groups are reported separately for that
    reason.
- **The Stripmap processing is new to this project.** Pre-run check 4 tests it
  on dry scenes, which cannot show whether flood water is detected correctly.
- **Test B is not blind,** and the three changes were written knowing the
  morning radar saw little water. Each change rests on evidence that is not
  radar (the calibration runs, the hourly records, the land cover, ANADEM's
  scatter), and none is tuned to test B. A reader should still weigh test B
  less than test A.
- **The joint highest pass** (4 February 2023, 377 cm) is lost to a 46-hour
  gap in the downstream record.
- **Velocities and depths are not tested** by anything in this design.

## Expectation, written before the run

- **The gate is the main risk.** The morning radar saw almost no open water.
  The evening passes are on average nearer the peaks and somewhat higher
  (median about 345 cm against 339 cm), and Stripmap resolves smaller
  patches. But it is the same valley at the same stages. A failed gate is
  about as likely as a pass.
- **If the gate passes,** criterion 2 (beating the benchmark) is still the
  hardest, as in run 1.
- **Test B** is most at risk at the higher morning passes (345–359 cm), where
  water over bank-level ground would exceed 0.5 m.
- **If test B fails,** the honest reading is that ANADEM's valley floor is
  still too low, and better ground heights, not model settings, are what
  would change the result.

## Decisions needed from you

1. **The three changes:** in-bank dry-floodplain start; floor no lower than
   the ordinary river level; fill hollows no deeper than 1.5 m. Approve all
   three, or name the ones to drop.
2. **Test B as an acceptance criterion:** water at least 0.5 m deep; median
   at most 0.10 km²; no more than 2 passes over 0.20 km². Approve it as a
   criterion, although it is not blind.
3. **Evening radar processing:** sarsen in a new pinned environment
   (recommended), or SNAP. Also approve the new 4-pixel patch rule and the
   cap of 8 dry references.
4. **The data gate:** at least 4 passes reach 0.1 km², and Spearman at least
   0.5. A failed gate ends run 2 with nothing shown.
5. **Keep run 1's 3-hour gap rule,** although it drops 4 February 2023
   (377 cm), 30 December 2022 and 11 June 2016.
6. **On acceptance:** show modelled depth and velocity, labelled "not
   tested", inside the tested extent (recommended, since you asked for
   velocity), or extent only.
7. **The downloads** in the table above.

## Approval (18 November 2026)

The project lead approved this design as drafted. The decisions above stand
as follows:

1. All three changes are approved: the in-bank, dry-floodplain start; the
   floodplain floor no lower than the ordinary river level; hollows no deeper
   than 1.5 m filled.
2. Test B is an acceptance criterion, as written, though it is not blind.
3. The evening scenes are processed with sarsen in a new pinned environment
   (`atibaia-sar`); SNAP 10 only if sarsen cannot read them. The 4-pixel
   patch rule and the cap of 8 dry references are approved.
4. The data gate is approved as written: a failed gate ends run 2 with
   nothing modelled shown.
5. Run 1's 3-hour gap rule is kept, so 4 February 2023, 30 December 2022 and
   11 June 2016 are not scored.
6. On acceptance, the viewer shows modelled depth and velocity inside the
   tested extent, labelled "not tested".
7. The downloads in the table are approved, the two conditional rows only if
   their condition arises.

From here, only the pre-run addendum may be added. Any other change to this
file is a new design for the project lead to approve.

## Pre-run addendum (in progress)

Started 18 November 2026. No evening (Stripmap) radar image has been
downloaded or looked at, and no run 2 event has been simulated.

### Check 1: evening Stripmap passes (done)

`pipeline/fetch_s1_sm_passes.py` searched Planetary Computer's
`sentinel-1-grd` catalogue (metadata only, one query per year, logged in the
manifest). It writes `docs/flood_run2_passes.md` and
`data/processed/flood_run2_passes.json`.

- **The catalogue:** 1,047 Stripmap scenes on ascending passes over the town
  from October 2014 to November 2026, on two relative orbits: 46 (21:35 UTC,
  beam S3, mostly HH/HV) and 119 (21:43 UTC, beam S6, VV/VH). It lists 58
  acquisitions twice (processed twice). One entry is kept per acquisition,
  the one geolocated with the precise orbit where there is one.
- **Which flood peaks (a reading of the design, fixed before any image):**
  the design says "each flood peak" and takes its expected candidates from
  `docs/flood_option_check.md` section 2, so the peak days of that table
  are used (daily mean stage; peaks less than 10 days apart count once).
  The alternatives were computed and are recorded: the project's 47-flood
  list (daily maximum, floods less than 10 days apart joined) would score
  19 passes; no peak window at all, 25. **For the project lead to confirm
  before check 6.**
- **Result:** 36 passes stood at 321 cm or more. **21 are scored**, at
  322.6–377.2 cm (median 342.7 cm). Excluded:
  - 8 for gaps in the 62671200 level over the event window: 11 June 2016
    (163 h), 30 December 2022 (12 h), 6 January 2023 (25 h), 4 February
    2023 (46 h), 15 March 2026 (5 h), and 11, 12 and 17 September 2026
    (8 h). No pass has a gap in the 3E-063 flow.
  - 3 for want of dry references: 14, 20 and 21 March 2026. No scene of
    the same orbit within 60 days found the river below 240 cm.
  - 4 not within a listed flood's window: 7 March 2016, 8 March 2017,
    4 January 2020 and 21 February 2020.
- **References:** 8 for 17 of the scored passes, and 3–6 for the other four
  (2025-02-05, 2026-02-01, 2026-02-12, 2026-02-13). **144 scenes to read** in
  all (the design estimated about 125).
- **Orbits:** most scenes were geolocated with the restituted orbit
  (RESORB). Precise orbits are fetched only if check 4 needs them.

### Check 2: LISFLOOD-FP outputs and restart (done)

`pipeline/flood_run2_lisflood_check.py`, on run 1's synthetic smoke channel
with n = 0.020 (`data/processed/flood_run2_lisflood_check.json`):

- **Floodplain velocity:** `voutput` writes `.Vx` and `.Vy` on cell faces,
  in m/s, but this build computes them **only with `hazard` switched on**.
  Without it they are written as zeros. With it, they agree with the
  model's own floodplain discharge: the median of
  |V| × depth × 20 m ÷ |Q| is 0.998 over 5,618 faces.
- **Channel velocity:** `SGCvoutput` writes `.SGCVx`, `.SGCVy` and
  `.SGCVc`, but they are zero in this build. The design's stated rule
  therefore applies: channel discharge (`qoutput`: `.Qcx`, `.Qcy`, m³/s on
  faces) ÷ (11 m × the cell's depth). On the synthetic channel the channel
  discharge is 15.0 m³/s (the inflow), giving 0.95 m/s at 1.43 m.
- **Restart:** `startfile` restores the channel depths exactly in 298 of
  299 channel cells, with the floodplain dry. The inflow cell holds 6.8 cm
  more because the inflow is added at t = 0; the run without a restart
  shows the same at its first output.
- **For run 2 (implementation, not a change of design):** every event run
  sets `voutput`, `qoutput` and `hazard`. Floodplain velocity comes from
  `.Vx`/`.Vy`, channel velocity from `.Qcx`/`.Qcy` by the rule.

### Check 3: terrain changes and the in-bank re-check (done)

`pipeline/flood_run2_terrain.py` (`data/processed/flood_run2_terrain.json`):

- **Mapped water:** 154 cells (0.06 km²), all from WorldCover; no OSM water
  polygon falls in the domain.
- **Change 2:** 4,403 floodplain cells (1.76 km²) raised to the ordinary
  river level, by a median 1.09 m (90th percentile 2.18 m).
- **Change 3:** 196 hollows (1.71 km²) filled to their spill level, by a
  median 0.42 m. 10 deeper hollows (0.43 km²) are kept, listed in the JSON
  file. On run 1's ground, before change 2, hollows no deeper than 1.5 m
  covered 0.45 km² and deeper ones 2.11 km²; the design's rough figures
  were 0.54 and 2.20 km².
- **Steady tests on the new ground (n = 0.020, 72 hours):**

| Flow (m³/s) | Stage at 3E-063 (m) | Error against the rating (m) | Calibration's error (m) | Floodplain over 10 cm (km²) |
| --- | --- | --- | --- | --- |
| 5 | 1.78 | +0.208 | +0.208 | 0.000 |
| 10 | 2.15 | −0.007 | −0.007 | 0.000 |
| 15 | 2.46 | −0.253 | −0.253 | 0.027 |

  **Passed:** the stage errors are unchanged, and the floodplain holds at
  most 0.027 km² against the 0.05 km² limit.

### Check 4: processing chain on dry scenes (failed as written; decision needed)

`pipeline/flood_sm_maps.py` (environment `atibaia-sar`, `envs/flood-sar.yml`;
results in `data/processed/flood_run2_check4.json`). Only dry scenes were read.
The two test scenes are the nearest dry references of the first scored pass on
each orbit: 7 January 2016 (orbit 46, HH, 174 cm) and 24 March 2016 (orbit
119, VV, 198 cm).

- **The chain as built:**
  - Each scene's annotation, calibration and noise files are read, plus a
    window of its measurement image around the town. The windows hold a
    standard SAFE folder on disk.
  - Thermal noise is subtracted with the scene's noise vectors (either
    annotation format), and the result calibrated to beta-nought.
  - sarsen 0.9.6 terrain-corrects it on GLO-30 + EGM2008 (ellipsoidal
    heights, 733–841 m) and flattens it to gamma-nought, on run 1's scoring
    grid.
  - To work, the environment needed four pins (in `envs/flood-sar.yml`), and
    the processing two fixes. sarsen returns the grid south-up. Planetary
    Computer's catalogue points newer products' annotation at the
    radio-interference report, so the files are found by their own names.
  - It reads Sentinel-1A and 1C, old and new annotation formats.

| Test (design) | Orbit 46, HH | Orbit 119, VV | Limit | Result |
| --- | --- | --- | --- | --- |
| Median gamma-nought on the scored ground | −7.1 dB | −9.2 dB | −11 to −5 dB | pass |
| Open water: the Salto Grande plant's pond (OSM way 31880069), 20 m in from the shore | −14.7 dB | −18.0 dB | below −15 dB | HH fails by 0.3 dB |
| Geolocation against run 1's orbit-53 `sentinel-1-rtc` dry median | 44 m | 43 m | within 10 m | fail |

- **The scoring grid holds no reservoir,** so the open-water test uses the
  pond 4.5–7 km below the station, on a small grid of its own.
- **Geolocation, checked against the optical geometry:**
  - The two new scenes agree with each other exactly (0 m, correlation 0.33
    to 0.50), despite different beams, polarisations and incidence angles.
  - Against the mapped buildings (13,982 footprints from run 1; radar is
    bright where they stand) they are within 2.4 and 3.3 m. Against
    WorldCover's water map, within 8 m.
  - **Run 1's morning radar reference is itself about 43 m west of the
    mapped buildings** (correlation 0.14), and about 100 m west of
    WorldCover's water (a weak match). The 43 m fails the test because the
    reference is off, not the new chain.
- **Open water in HH, other dry scenes** (diagnostic, not in the design):
  - Two later dry HH scenes read the pond at −17.6 dB (16 March 2019) and
    −16.8 dB (8 January 2026, Sentinel-1C). The HH chain does read open
    water dark; the 7 January 2016 pond read brighter.
  - Noise removal darkens that 2016 reading from −13.3 to −14.7 dB, so the
    noise step works.
- **What it implies for run 1 and test B:**
  - Run 1's morning flood maps were made on that reference stack, so they
    sit about 43 m west of its scoring mask and model grid.
  - Test B's acceptance uses only the modelled water, so it is unaffected.
    The CSI against the morning maps that test B reports would be.
- **For the project lead:** the design says to fix the processing, or fall
  back to SNAP, if a test fails. The evidence says the processing is sound
  and the reference image is not. Before check 6 the lead decides: accept
  this chain, with geolocation judged against the mapped buildings and the
  HH open-water evidence above; fall back to SNAP; or stop run 2.

### Check 5: the scored list (done, pending the flood-peak confirmation)

The gap rule was applied in check 1. With the option check's flood peaks, 21
passes are scored (11 HH/HV, 10 VV/VH). With the project's flood list it
would be 19, and with no peak window 25. The list is fixed once the project
lead confirms the peak list.

### Decisions by the project lead (18 November 2026, before any flood scene was read)

1. **Check 4: the processing chain is accepted.** Geolocation is judged
   against the mapped buildings (2.4 and 3.3 m, within the 10 m limit), not
   against run 1's morning reference, which is itself about 43 m west of
   them. HH open water is accepted on the two later dry HH scenes (−17.6 and
   −16.8 dB at the pond). The chain is used unchanged for check 6.
2. **Flood peaks: the option check's list** (`docs/flood_option_check.md`
   section 2). The scored list is the 21 passes in `docs/flood_run2_passes.md`.

### Check 6: the evening flood maps and the data gate (done: **the gate failed**)

`pipeline/flood_sm_maps.py maps` processed all 144 scenes (the 21 scored passes
and their dry references) by the accepted chain, with no scene error. It wrote
`data/processed/flood_run2_observed.tif` and `.json`, and
`docs/flood_run2_observed.png`. Every pass has radar data on all 15,893 cells
of the scoring mask, which is run 1's mask less 485 cells of mapped permanent
water. Each pass has 3–8 dry references.

- **Flooded pixels on the mask**, by the fixed rule (at least 3 dB below the
  reference, below −15 dB, in patches of at least 4 pixels): **0 to 25 per
  pass, at most 0.0025 km²**. Before the patch rule, 0 to 32 pixels were
  flagged. The highest pass, 12 February 2026 at 377 cm, has 11 pixels.
- **G1:** no pass reaches the 1,000 pixels (0.1 km²) needed to be scored,
  against the 4 required. **Failed.**
- **G2:** across the 21 passes, the Spearman correlation between the flooded
  pixels and the stage at the pass is **0.08**, against 0.5 required.
  **Failed.**

**By the design, run 2 is not accepted.** There is no extent test, and
nothing modelled is shown. The evening maps are reported here, not shown in
the viewer. **The finding:** at these stages (322–377 cm at 3E-063, up to
0.76 m over the overflow level), the radar sees no broad open water on the
open valley floor, morning or evening. That holds for C-band Stripmap at
about 23 m resolution, HH or VV, and for run 1's wide-swath morning passes.
Water in grass, under trees or in streets is not tested by any of them.

**Still to do by the design:** test B (no false flooding at the 13 morning
passes) "is still run and reported, as information". It needs the run 2
model built and run for the 13 morning events, then the verdict file
`data/processed/flood_run2_verdict.json` (`"passed": false`), written once.
