# Flood model, run 1 (Atibaia town, SFINCS): design and test, fixed before any run

Drafted 17 November 2026. **Status: approved by the project lead on
17 November 2026, before any code was written.** Nothing has been built or
run. **No radar image has been downloaded or looked at**, so the main test
below can still be blind. From here on, the only additions allowed are the
pre-run addendum, and nothing in this file may be changed after any modelled
flood map has been compared with an observed one.

The data behind this design are in `docs/flood_option_check.md`. The model
was chosen there (section 5) and by the project lead on 17 November 2026.

## What run 1 is, stated plainly

- A 2D flood model of the Rio Atibaia through Atibaia town, from about 1.5 km
  above SP Águas' gauge 3E-063 to the Salto Grande plant, about 6 km below it.
  It is driven by **measured** flow at the town gauge, not by modelled
  inflow. It is independent of the inflow models in runs 1–4.
- **The claim it seeks:** given the measured flow at the town gauge, the model
  maps which open ground is under water during a flood, **better than a map
  made from the terrain alone**. If it cannot beat that terrain-only map, the
  hydraulics add nothing here, and that is a result worth having.
- **Not claimed, even on a pass:** depths, flooding of streets and buildings,
  timing, floods larger than those tested, or any forecast.
- **The main weaknesses are known in advance.** Ground heights come from a
  30 m model with errors of metres, while the imaged floods stand 0.2–0.8 m
  above the overflow level. About 190 km² of tributaries are ungauged. The
  level at the downstream end is controlled by a plant whose structure has
  not been located. The discharge above the overflow level rests on a rating
  segment unchanged since 2002.

## Reach, grid and software

- **Domain:** a corridor along the Rio Atibaia, from 1.5 km upstream of
  3E-063 (nothing larger than 5.5 km² joins in that stretch) to the
  downstream boundary set by pre-run check 4. Lateral limit: cells within
  2 km of the river and no more than 15 m above it (height above nearest
  drainage on ANADEM). Projection: SIRGAS 2000 / UTM 23S (EPSG:31983).
- **Grid:** SFINCS regular grid of 25 m compute cells in **subgrid mode**,
  with subgrid tables built from the 5 m composite terrain below. No
  quadtree in run 1.
- **SFINCS v2.5.0**, the Windows executable from Deltares. It is used, not
  redistributed (Deltares freeware licence; the source is GPL-3.0). Its
  SHA-256 goes into `data/raw/manifest.jsonl`.
- **Tooling, needs approval:** building the subgrid tables by hand would be
  error-prone, so the model is built with **HydroMT-SFINCS** (v2.0.0, as
  recommended by the SFINCS v2.5.0 release notes) in a pinned conda
  environment. The environment file is committed. This is the first part of
  the project that is not standard-library Python or the existing Node tools,
  and it is confined to building the model. Fetching, scoring and the
  viewer stay as they are.

## Terrain: the 5 m composite

All rules fixed here and applied before any run.

| Layer | Source | Rule |
| --- | --- | --- |
| Ground | ANADEM (bare earth, 30 m) | Resampled bilinearly to 5 m. This adds no information; it only carries the finer layers |
| River channel | OSM river line, and river-area polygons where mapped | Width from the OSM polygon where mapped, otherwise measured on the August 2024 Sentinel-2 composite every 250 m; listed in the addendum. Bank height: the lower of the two ANADEM values 30 m outside each bank, smoothed so it never rises downstream. Bed = bank − **2.11 m** |
| Buildings | OSM footprints, plus Microsoft footprints that do not overlap an OSM one | Raised by 10 m (they block flow and hold no water) |

The 2.11 m channel depth comes from SP Águas' data at 3E-063, not from any
fit: overflow level 3.01 m minus the zero-flow stage of the last published
low-flow rating segment (0.90 m, 2019–2020). It is applied along the whole
reach.

## Flows and boundaries

- **Inflow:** hourly discharge at 3E-063 from SIBH, as served, entered at the
  upstream end of the domain.
- **Tributaries:** five discharge points at the junctions found on the DEM
  (27, 107, 8, 43 and 4 km²; exact cells listed in the addendum). Flow at each
  is the junction's area times the local specific discharge above the town:
  (hourly flow at 3E-063 − same-day Cachoeira and Atibainha releases) ÷
  431 km² (the land above the gauge not behind a dam: 1,141 − 397 − 313),
  set to zero if negative. This is a scaling of measured flow, not a
  rainfall-runoff model. Rain on the grid is switched off. The 5.5 km²
  stream that joins at the gauge itself is ignored.
- **Downstream boundary**, decided by pre-run check 4, by this rule:
  - If the plant's weir or dam is found within 1.5 km below the Salto Grande
    station **and** its crest or normal water level can be found in a public
    source (ANEEL or CPFL), the domain ends 500 m below it with an outflow
    boundary (SFINCS outflow cells, confirmed in check 5), and the weir is
    modelled at that crest. The station's level then becomes test 2 below.
  - Otherwise the domain ends at the Salto Grande station, with its observed
    hourly level (ANA 62671200; SAISP 814 is not used) as a water-level
    boundary. Its datum is tied to ANADEM's surface on the river at the
    station (the median observed level is set equal to it). That tie is
    approximate, which is why the ±0.5 m variation is run. Test 2 is then not
    possible.
- **Start of each flood run:** 72 hours before the radar pass, from a steady
  state at that hour's flows.

## Roughness and the one calibrated parameter

- **Floodplain roughness:** fixed by land cover (ESA WorldCover 2021), Manning
  n: tree cover 0.10, shrubland 0.07, grassland 0.035, cropland 0.035,
  built-up 0.05, bare 0.03, wetland 0.06, water 0.03.
- **Channel roughness: the only calibrated parameter.** It is tuned on
  in-channel flow only, against SP Águas' rating at 3E-063 (last low-flow
  segment, Q = 7.8 (h − 0.90)^1.1). The targets are stage at 5, 10 and
  15 m³/s: 1.57, 2.15 and 2.71 m on the gauge scale. The model's gauge scale
  is tied by setting the model bank at the gauge to 3.01 m. n from 0.025 to
  0.080 in steps of 0.005; pick the lowest root-mean-square stage error, from
  steady runs.
- **No flood is used for calibration, so every flood image below is a test.**

## Observed flood maps, fixed before any model run

Made and committed, with the counts per pass, before any modelled map
exists.

- **Images:** Planetary Computer `sentinel-1-rtc` (terrain-corrected, 10 m,
  CC BY 4.0), VV polarisation.
- **Passes scored:** every wide-swath pass found by the search behind
  `docs/flood_option_check.md` section 2 (2 days before to 6 days after each
  of the 30 flood peaks since October 2014) taken while 3E-063 stood at least
  **0.2 m above the overflow level (321 cm or more)**. That section's table
  shows only the best pass per flood; the list here includes every
  qualifying wide-swath pass. That is 17 passes in 16 floods:

  | Pass (UTC) | Stage at pass (cm) |
  | --- | --- |
  | 2016-01-20 08:30 | 327 |
  | 2016-02-25 08:30 | 339 |
  | 2017-01-14 08:30 | 324 |
  | 2017-01-26 08:30 | 346 |
  | 2018-02-02 08:30 | 336 |
  | 2018-03-04 08:30 | 333 |
  | 2019-03-05 08:31 | 345 |
  | 2020-02-28 08:31 | 359 |
  | 2021-01-17 08:31 | 340 |
  | 2023-10-10 08:31 | 348 |
  | 2024-12-27 08:31 | 326 |
  | 2026-02-02 08:30 | 325 |
  | 2026-02-14 08:30 | 350 |
  | 2026-02-26 08:30 | 324 |
  | 2026-03-15 08:38 | 353 |
  | 2026-03-16 08:31 | 340 |
  | 2026-09-13 08:30 | 377 |

  Passes at 0.2 m or less above the overflow level (2016-06-12, 2022-02-05,
  2026-09-18, 2026-10-25) are not scored.
- **Reference (dry) image:** for each pass, the median of all passes of the
  same relative orbit within 60 days either side with 3E-063 below 240 cm
  (below the attention level). At least three are required; otherwise the
  pass is not scored.
- **Flooded pixel:** VV at the pass at least 3 dB below the reference **and**
  below −15 dB. Open water only; flooded vegetation that brightens is not
  detected, and that is accepted.
- **Scoring mask:** inside the model domain, excluding the river channel
  (OSM river area or line plus 15 m), built-up land (WorldCover class 50),
  building footprints plus 20 m, tree cover (class 10, radar cannot see
  under it), and slopes over 10° on ANADEM.
- **A pass is too small to score** if fewer than 1,000 pixels (0.1 km²) in
  the mask are flooded. It is reported, not scored.
- **Data gate (no model involved):** across the scored passes, the observed
  flooded area must rise with the stage at the pass (Spearman correlation at
  least 0.5). If it does not, the radar maps are not measuring the flood,
  run 1 stops, and there is no model test.

## The test, fixed here

Each modelled map is the water at the time of the pass, central run, on the
10 m radar grid. A cell counts as wet if the modelled depth is over 10 cm.

- **Critical success index (CSI)** per pass, on the scoring mask:
  both wet ÷ (both wet + only modelled wet + only observed wet).
- **Terrain-only benchmark**, also made before any model run: a cell is wet
  if its height above the river (height above nearest drainage on ANADEM,
  river cells draining at least 1,000 km²) is no more than
  (stage at pass − 3.01 m) + H, where H is that height for the bank cells at
  3E-063.

**Accepted only if all three hold:**

1. Median CSI over the scored passes at least **0.45**.
2. The model beats the benchmark: median CSI at least **0.05** higher, and
   a higher CSI on at least **two-thirds** of the scored passes.
3. Median ratio of modelled to observed flooded area between **0.67 and
   1.5**.

**Test 2, only if the downstream boundary is the plant's weir:** the rise in
level at the Salto Grande station from 72 hours before each pass to the
pass, modelled against observed. Reported with its median error; it is not
an acceptance criterion in run 1, because the weir crest will be uncertain.

The thresholds are judgements. Studies with good terrain often reach CSI
values of 0.6–0.8; with 30 m ground in a flat valley, 0.45 is a modest bar.
The benchmark criterion matters more: it asks whether the hydraulics earn
their keep.

## Reported, not scored

The same scores for these variations, one at a time: inflow × 0.8 and
× 1.25 (the rating above the overflow level); tributary flows × 0.5 and × 2;
downstream level ± 0.5 m (if a level boundary is used); buildings removed;
channel n ± 0.010. Also reported: the fraction of variations in which each
cell is wet, as an uncertainty band; and the flow at which the model first
puts water out of the channel at 3E-063, which is near the observed 20–24 m³/s
largely by construction, so it is a check, not a test.

## Pre-run checks (no comparison with observed flood maps)

Recorded in an addendum to this file and committed before any modelled map
is compared with an observed one.

1. ANADEM downloaded and logged in the manifest; the river's bank profile
   plotted.
2. The channel width table and the five tributary cells listed.
3. Every pass in the table confirmed in `sentinel-1-rtc`, with its reference
   passes; observed maps made, counted and committed; the data gate run.
4. The plant's structure located (OSM, imagery, ANEEL and CPFL public
   documents); the downstream boundary chosen by the rule above and recorded
   with its evidence.
5. SFINCS and HydroMT-SFINCS versions pinned and hashed; one test model
   built and run to check that the outflow or water-level boundary behaves
   (a steady run at 15 m³/s must hold a stable level).
6. Hourly SIBH flow at 3E-063 and level at 62671200 fetched through the
   pipeline (logged in the manifest) for every pass window.

If check 3's data gate fails, or check 5 cannot be met, run 1 stops and a
revised design is needed.

## Outcome rules

- **Accepted.** The model may map flood extent on open ground in this reach
  for town-gauge stages from 321 to 377 cm (the tested range), given the
  measured flow. The viewer may show it for replayed dates in that range,
  labelled **"modelled: flood run 1; open ground only; 30 m ground heights;
  tributary inflow estimated"**. Built-up land is drawn as not tested. No
  depths are shown. Nothing is shown outside the tested range.
  `tests/test_pipeline.py` is extended so that no flood layer reaches the
  viewer without an accepted run.
- **Not accepted.** Nothing modelled is shown. No re-tuning: a revised model
  is a new run with its own design.
- **Either way**, the observed radar flood maps are data, not model output.
  They may be shown in the viewer on their dates, labelled **"derived from
  Sentinel-1: open water on open ground"**, once the data gate has passed.

## Expectation, written before the run

- The data gate should pass: the floods are large on the gauge, and the
  valley has open pasture near the river.
- Criterion 1 is uncertain. The ground heights are the main risk.
- Criterion 2 is the hardest. On a flat 6 km reach, the water surface at the
  peak is nearly level, which is what the terrain-only map assumes. The
  model should do better where tributary inflow or the downstream control
  shapes the water surface, and worse if the tributary scaling is wrong.
- If the model fails criterion 2 but meets 1 and 3, the honest reading is
  that a terrain-only map is as good as the hydraulics on this terrain, and
  better ground heights are what would change that.

## What this design does not fix

- Ground heights. Survey or lidar data for the town (municipality, the state
  cartographic institute, or CPFL's licensing surveys) would matter more than
  any model setting.
- Tributary inflow is scaled, not measured.
- Discharge above the overflow level comes from a rating segment unchanged
  since 2002.
- Radar detects open water only; flooded vegetation and streets are missed.
- Rain falling directly on the floodplain is not modelled. Where it ponds,
  the radar will see water that the model cannot produce.
- Only the 05:30 local-time wide-swath passes are used. The early-evening
  Stripmap passes would need processing from raw scenes and are left for a
  later run.

## Pre-run addendum (in progress)

Started 17 November 2026. No radar image has been downloaded or looked at,
and no model has been built.

### Check 6: station records (done)

`pipeline/fetch_flood_stations.py` fetched SIBH's hourly records for 3E-063
(1 January 2015 to 17 November 2026, 102,333 hours) and ANA 62671200 (from
1 March 2015, 88,909 hours), logged in the manifest. `pipeline/flood_passes.py`
writes them as `data/processed/flood_hourly_3E-063.csv` and
`flood_hourly_62671200.csv`.

In the 72 hours before each pass that qualifies under check 3, the flow at
3E-063 is complete. The level at 62671200 is complete except on three passes:
28 February 2020 (one hour missing), 10 October 2023 (no record at all) and
13 September 2026 (30 consecutive hours missing).

### Check 4: downstream boundary (done)

- No dam, weir or power plant is mapped in OpenStreetMap within 5 km of the
  station.
- An unnamed 1.0 km² OSM water body tagged as a reservoir (way 31880069)
  lies along the river about 4.5–7 km below the station, 2.4 km long. It is
  very probably the plant's pond, which would put the dam about 7 km below
  the station.
- No public crest or normal water level was found. A web search found
  documents only for CPFL's Americana plant (the "Salto Grande" reservoir
  at Americana, about 60 km downstream), and ANEEL's open-data server did
  not respond on 17 November.
- The 90 m surface model and ANADEM show no fall within the reach.

**Outcome by the design's rule:** the structure is not within 1.5 km of
the station with a public crest level, so the domain ends at the Salto
Grande station with its observed hourly level as a water-level boundary,
tied to ANADEM as stated. Test 2 is not possible.

### Check 3, first half: passes and dry references (done)

`pipeline/fetch_s1_passes.py` fetched the catalogue entries; the table is
`docs/flood_run1_passes.md`. **15 of the 17 passes qualify:**

- **15 March 2026, 08:38:** not in `sentinel-1-rtc` (its orbit, 126, is not
  processed there).
- **16 March 2026:** has one dry reference against the three required.

All qualifying passes are on relative orbit 53 (descending, 05:30 local
time). Their stage in the hour of the pass is 324–377 cm, and their flow is
18.5–34.6 m³/s.

### Check 1: terrain (done)

- **ANADEM was read, not downloaded whole.** The zone 23K file is 2.05 GB,
  tiled internally and served with byte-range support. Only the six tiles
  covering the window were read: 4.0 MB, each logged with its byte range
  and SHA-256 (`pipeline/fetch_anadem_window.py`). The window is 818 × 557
  cells, 721.7–1,395.6 m, with no gaps.
- **Profile along the OSM river line** (`pipeline/flood_terrain.py`;
  `docs/flood_run1_profile.svg`, `data/processed/flood_run1_profile.csv`).
  From the gauge to the station is 7.3 km along the line. ANADEM falls from
  745.8 m at the gauge to 743.1 m at the station, about 2.7 m. Along the
  line it varies between 740.7 and 749.5 m, which is the noise the design
  warned of. GLO-30 reaches 770 m at tree and building spikes; ANADEM
  removes them, and the median difference on the line is −0.3 m.

### Rule added: gaps in the downstream level (approved 17 November 2026)

The approved design did not say what happens if the boundary record has a
gap. This rule was proposed and **approved by the project lead on
17 November 2026, before any model or image existed**:

> A gap of up to 3 consecutive hours in the 62671200 level within a pass's
> 72-hour window is bridged linearly, for the boundary input only. A pass
> with a longer gap is not scored.

Its effect was known when it was approved. 28 February 2020 stays in.
10 October 2023 and 13 September 2026 (the highest flood, 377 cm) are
dropped, leaving **13 scored passes**. Bridging the 30-hour gap was not
proposed: the downstream level sets the backwater through the reach, so an
invented level would decide the result. `pipeline/flood_passes.py` applies
the rule, and `docs/flood_run1_passes.md` lists the outcome for every pass.

### Check 5, first half: SFINCS and HydroMT-SFINCS (done)

- **SFINCS v2.5.0 runs from the official Docker image**, not the Windows
  executable named above: Deltares' download portal could not be reached
  from this machine. Same version, same publisher; the image is the route
  given in the v2.5.0 release notes. Image
  `deltares/sfincs-cpu:sfincs-v2.5.0-Hautacam`, digest
  `sha256:ad4f57175b317ec51b8fe6bc3af5079f958c206ffe1308fbce5bc7e8abc479f3`
  (781 MB unpacked). The binary reports build "v2.5.0 Hautacam Release
  2026.02", 30 October 2026. Running it accepts the Deltares SFINCS FreeWare
  licence, as the design stated.
- **HydroMT-SFINCS 2.0.0** with HydroMT 1.4.1, Python 3.12.16, GDAL 3.13.3,
  in the conda environment `atibaia-sfincs` (`envs/flood-sfincs.yml`; exact
  versions in `envs/flood-sfincs.lock.txt` and `envs/flood-sfincs.pip.txt`).
  Two fixes were needed:
  - HydroMT-SFINCS imports IPython and datashader without declaring them, so
    both were added to the environment.
  - `C:\OSGeo4W\bin` on the system PATH supplies a different GEOS library.
    It is removed from PATH for the model-building process only; the system
    PATH is untouched.
- **Engine smoke test passed** (`pipeline/flood_sfincs_smoke.py`). The case
  is a synthetic 2 km channel: 15 m³/s in, a fixed water level at the outlet,
  12 hours.
  - The level half-way down changed by 0.0 cm over the last 2 hours.
  - The discharge through a cross-section there was 15.00 m³/s.
  - The first run read 30 m³/s because the section line lay on cell
    centres, where SFINCS counts the faces on both sides. On a cell face it
    reads correctly. The model's own cross-sections must follow the same rule.
- **Still to do for check 5:** the steady 15 m³/s test on the real domain,
  which needs the composite terrain and so check 2.

### Check 2: widths, tributary points, bank and bed (done, with two approved changes)

`pipeline/flood_channel.py`. No radar image or model output is used.

**The width rule failed, as written.**
- OSM maps no river polygon in the reach, so every width had to come from
  Sentinel-2. The rule was fixed in the script before any width was
  computed: the same four August 2024 scenes as the viewer, at their native
  10 m; water where the median NDWI is above 0; transects every 250 m.
- **None of the 36 stations shows water.** The highest NDWI within 10 m of
  the line is −0.56 at the median station and −0.03 at best, against about
  −0.75 over the surrounding vegetation. The river is narrower than a pixel
  or hidden under riverside trees in the dry season. By its own terms
  (fewer than half the stations with a width) the rule failed.
- A code fault was found and fixed on the way. Earth Search marks these
  scenes as already carrying the reflectance offset, and the first run
  applied it again (NDWI came out below −1). That is a fault in reading the
  scenes, not a change of rule, and the script now stops if NDWI leaves
  [−1, 1]. The result above is from the corrected run.
- ANA's discharge-measurement summaries, which would give measured widths
  at gauge 62670000, are behind a login on HidroWeb (HTTP 401).

**Change approved by the project lead on 17 November 2026**, before any
model or image existed:

> Channel width is **11 m along the whole reach**, from the OpenStreetMap
> `width` tag on the Rio Atibaia (ways 683621553 and 589992966). The reported
> variations gain width × 0.67 and × 1.5 (7 and 17 m). The channel roughness
> is calibrated with whichever width is used.

A check using no model, only data already in hand: with SP Águas' last
low-flow rating at 3E-063 (Q = 7.8 (h − 0.90)^1.1), 11 m implies mean
velocities of 0.75 m/s at 15 m³/s (1.81 m deep) and 0.76 m/s at the overflow
level (17.7 m³/s, 2.11 m deep). With the ANADEM slope of about 1 in 2,700,
that corresponds to a channel Manning n of 0.031–0.034, an ordinary value
for such a river. The 11 m is a mapper's
estimate and is the same on every way, so it is a reach-average figure at
best.

Also seen in OSM: a two-point stretch of the river tagged as a culvert
(way 589992967) at the Salto Grande station, probably a road crossing. It
lies on the domain's downstream boundary, where the observed level is
imposed, so it does not enter the model.

**Tributary points (done):** the junctions on the 90 m flow path, moved onto
the OSM line (`data/processed/flood_run1_tributaries.json`). Distances run
along the OSM line, which meanders more than the 90 m path:

| Tributary | Below 3E-063 along the line | Moved onto the line by |
| --- | --- | --- |
| 26.5 km² | 1.72 km | 97 m |
| 106.7 km² | 3.59 km | 59 m |
| 8.1 km² | 6.69 km | 68 m |
| 42.6 km² | 7.16 km | 108 m |
| 3.7 km² | 7.42 km | 293 m |

The 3.7 km² junction maps 0.1 km beyond the Salto Grande station (7.3 km
along the line), outside the domain, so **four tributary inflows** enter
the model.

**Bank and bed (11 m width applied; one reading needs a decision).** Every
30 m, the raw bank is the lower of ANADEM 35.5 m either side of the line
(half the width plus 30 m). It ranges 740.2–747.5 m. The design says the bank
is then "smoothed so it never rises downstream". Two readings were computed
(`data/processed/flood_run1_channel.csv`, chart `docs/flood_run1_channel.svg`):

| Reading | Top of reach | At 3E-063 | At 62671200 | Raw bank minus this: median (10th–90th percentile) |
| --- | --- | --- | --- | --- |
| Running minimum (first run) | 747.07 m | 741.57 m | 740.19 m | +2.22 m (+0.44 to +3.76) |
| Least-squares fit that never rises (isotonic) | 747.11 m | 744.85 m | 742.19 m | +0.05 m (−1.66 to +1.24) |

The running minimum follows the lowest noise dips in ANADEM and stays
there, so it sits a median 2.2 m below the measured bank. Under it the
channel would in effect be about 4.3 m deep against the ground beside it,
and the model would rarely overflow. The isotonic fit is unbiased; its
scatter is the ANADEM noise the design already warns of.

**Reading approved by the project lead on 17 November 2026**, before any
model or image existed: "smoothed so it never rises downstream" means the
isotonic (least-squares, never-rising) fit. The bed is that bank minus
2.11 m. The bank at 3E-063 is 744.85 m and the bed 742.74 m, so the gauge's
zero sits at 741.84 m on the ANADEM datum (bank = 3.01 m on the gauge
scale). At the Salto Grande station the bank is 742.19 m and the bed
740.08 m. The running minimum stays in the output for the record only.

**Check 2 is done.**

### Model build and check 5, second half (built; structural problem found)

`pipeline/flood_build_model.py` (atibaia-sfincs environment), model folders
under `models/flood_run1/` (not committed). No radar image or observed flood
is used.

**What was built, as designed:**
- **Domain:** 8.7 km². Height above the river is measured to the OSM line,
  because ANADEM's flow paths in this window cannot reach the design's
  1,000 km² threshold (most of the catchment lies outside the window). The
  height-above-river raster is kept for the terrain-only benchmark.
- **5 m composite terrain** (EPSG:31983): 1,065 × 910 pixels. The 11 m
  channel is cut in on 4,364 pixels. Buildings are raised 10 m on 160,868
  pixels: 986 OSM footprints plus 17,676 Microsoft footprints (780
  overlapped OSM and were dropped).
- **Roughness** from WorldCover (`data/raw/worldcover/`, read by
  `pipeline/fetch_flood_landcover.py`).
- **SFINCS model:** 213 × 182 cells of 25 m in subgrid mode, four tributary
  inflows plus the upstream inflow, and water-level boundary cells across
  the valley at the Salto Grande station.

**Implementation details that differ from the text above:**
- HydroMT-SFINCS requires an even number of subgrid pixels per cell, so the
  tables use 6 (4.2 m) resampled from the 5 m composite.
- The first build selected no boundary cells (a geometry error of mine), so
  SFINCS ran with its outlet closed. Fixed.

**Steady test passed** at 5 days of 15 m³/s: every level changed by ≤ 0.1 cm
over the last 2 hours, and 14.5 m³/s crossed the gauge section. Runs of 24 h
and 72 h were too short. The downstream level used was provisional (see
below).

**But the model cannot carry the river in its channel.**

| Test at 15 m³/s | Level at 3E-063 on the gauge scale | SP Águas' rating |
| --- | --- | --- |
| As built, channel n = 0.035 | 3.86 m (0.85 m above the overflow level) | 2.71 m (in-channel) |
| Channel n = 0.010 / 0.200 | 3.74 m / 4.20 m | 2.71 m |
| Advection off | 3.48 m | 2.71 m |
| Buildings removed | 3.70 m | 2.71 m |
| 10 m grid; 50 subgrid levels | 3.92 m; 3.92 m | 2.71 m |

- A 20-fold change in channel roughness moves the gauge level by only
  0.46 m, so calibrating the roughness cannot bring the model to the
  rating.
- **Channel-only diagnostic.** With everything but the channel raised
  20 m, 15 m³/s stands **5.85 m** deep at the gauge (25 m grid), **5.20 m**
  (10 m grid) and **8.58 m** (5 m grid, not steady after 24 hours). Manning's
  equation for an 11 m channel at the reach's average slope gives about
  1.95 m, and the rating implies 1.81 m. The subgrid "mean" weighting gives
  4.46 m: better, still far off.
- **Reading:** on a square grid, SFINCS gives this narrow, meandering channel
  a fraction of its real conveyance. Where the channel crosses cell faces at
  an angle, the face's passage is assembled from pixel rows that do not
  follow it; on fine grids the channel becomes a staircase joined
  corner-to-corner. As built, the model would overflow at roughly half the
  real flow and overstate every flood. This is a structural limit of the
  model chosen for this reach, not something calibration can fix.

**Also found: the datum tie at 62671200 cannot work as written.** ANADEM's
surface on the river line at the station (743.1 m) is above the bank
(742.19 m), because the 11 m river is not resolved in a 30 m terrain model.
Setting the station's median level to it would put the boundary above the
bank permanently. A different tie is needed whichever model is used.

**Decision needed: the model.** Two candidates were set aside earlier for
reasons that now matter less than this:
- **LISFLOOD-FP 8.2 with its subgrid channel.** The channel is a 1D network
  along the river, with its own width, bed and length, coupled to a raster
  floodplain. It was designed for rivers narrower than the grid, and this
  design's inputs (11 m width, bed profile, ANADEM, buildings) map straight
  onto it. It has to be built from source; Docker is installed, so a Linux
  build avoids Visual Studio.
- **ANUGA** with a mesh that follows the channel (breaklines, small
  triangles along the river). It is Python, installs from pip, and its
  structures would suit the plant's weir later. It is slower, and the mesh
  takes more care.

The domain, composite terrain, roughness, height-above-river raster, inflow
points and the pass table are independent of the model and carry over.

**Decision (17 November 2026):** the project lead chose **LISFLOOD-FP 8.2
with its subgrid channel**, before any model output or radar image had been
compared with anything. SFINCS is set aside for this reach. The test,
criteria, passes and benchmark are unchanged. How the model's own inputs are
set up (grid size, channel cells, buildings) is recorded below before any
run on the real domain.

### LISFLOOD-FP 8.2: build and smoke test (done)

- **Source:** the official 8.2 release on Zenodo (10.5281/zenodo.13121102,
  "LISFLOOD-FP developers", GPL-2.0; same record family as the 8.0 release).
  `LISFLOOD-FP-v8.2.zip` is 348,144,517 bytes; its MD5 matches Zenodo's
  (`a0a607cf…cafa95`) and its SHA-256 is `79820721…2bc6bae3`. It is not in
  git.
- **Build:** CPU-only, in Docker from `envs/lisflood-fp.Dockerfile`
  (Ubuntu 24.04, CMake, NetCDF). The image is `atibaia/lisflood-fp:8.2`,
  digest `sha256:a6fbe6ac…24295240`. The binary prints "version 8.1.0":
  the release's internal version string was evidently not updated.
- **Units:** point inflows (`QFIX`, `QVAR`) are per metre of cell width.
  The first smoke run passed 15 and received 300 m³/s on 20 m cells. The
  real model's inflows are divided by the cell size, and the script now
  checks the mass file's inflow.
- **Smoke test passed** (`pipeline/flood_lisflood_smoke.py`). The case is a
  synthetic sine-wave channel, 11 m wide and 2.11 m deep, more sinuous than
  the Atibaia, on 20 m cells, with 15 m³/s. Depth mid-channel was 2.00 m
  (steady) with only the channel open, against Manning's 2.16 m; it was
  also 2.00 m with the floodplain open. Mass balance: 15.00 m³/s in and
  out. This is the test SFINCS failed, at 5.2–8.6 m.

### LISFLOOD-FP setup (approved 17 November 2026)

The design's rules are kept. These model-specific choices, and the datum tie
below, were **approved by the project lead on 17 November 2026**, before any
run on the real domain:

| Item | Proposal |
| --- | --- |
| Grid | 20 m cells, EPSG:31983, covering the same 8.7 km² domain (the channel must be narrower than a cell, so cells at least 11 m) |
| Floodplain ground | ANADEM resampled bilinearly to 20 m (ANADEM holds nothing finer) |
| Buildings | Cells at least half covered by footprints (OSM, plus non-overlapping Microsoft) raised 10 m; the rest left as ground with the built-up roughness |
| Channel | A 4-connected path of cells following the OSM line from 1.5 km above 3E-063 to the station. Width 11 m; bank = the approved isotonic bank at the cell's position along the line; bed = bank − 2.11 m |
| Floodplain roughness | The design's WorldCover table, by the majority class in each cell (`manningfile`) |
| Channel roughness | `SGCn`, the one calibrated parameter, 0.020–0.080 in steps of 0.005, against the rating at 5, 10 and 15 m³/s |
| Inflows | `QVAR` at the upstream channel cell and the four tributary channel cells, as discharge ÷ 20 m |
| Downstream | `HVAR` at the station's channel cell, from the observed hourly level at 62671200 and the tie below |
| Solver | Acceleration (local inertial) with the subgrid channel, CPU |

**Datum tie at 62671200, replacing the one that cannot work:** the station's
median observed level (2015–2026) is set equal to the station's bed plus
the median depth at the town gauge over the same hours (3E-063's stage minus
its zero-flow stage, 0.90 m). In words: in ordinary flow the river is taken
to be as deep at the station as at the town gauge. It ignores the plant's
pond, which would make the station deeper, so it is likely to place the
boundary too low. The design's ±0.5 m variation brackets that.

### LISFLOOD-FP model of the reach and steady test (done)

`pipeline/flood_lisflood_build.py`; model folders under
`models/flood_run1/lisflood/` (not committed). No radar image or observed
flood is used.

- **Grid:** 267 × 228 cells of 20 m, 21,737 of them inside the domain;
  outside it, a wall.
- **Channel:** a path of 566 cells. 18 cells where meanders loop back were
  skipped, and 13 places have adjacent loops the model may use as
  cut-offs. The path is 11.3 km long against 8.8 km along the OSM line,
  because it follows the cells as a staircase, so the model sees a gentler
  slope than the river. The channel roughness is calibrated with it.
- **Buildings:** 2,559 cells raised.
- **Implementation details not spelled out in the approved setup:**
  - Each channel cell's ground is set to its bank, so the water leaves the
    channel at the bank level, as the design defines it.
  - The downstream level is imposed on the 28 domain cells within 20 m of
    the station along the line, across the valley.
- **Datum tie at 62671200**, by the approved rule, over 87,152 hours both
  stations report: the median depth at 3E-063 is 1.288 m, and the median
  level at 62671200 is 2.830 m on its gauge. With the bed at the station at
  740.08 m, the station's zero sits at **738.54 m**.
- **Downstream level in steady runs** (an implementation detail, chosen
  before any steady result was seen): the median station level in the
  hours when 3E-063 carried that flow (±10%), through the tie. For
  15 m³/s it is 741.70 m (median of 5,352 hours).

**Steady test passed** at 10 days of 15 m³/s, n = 0.035. Every level is
steady to ≤ 0.1 cm over the last 2 hours, and 15.02 m³/s in matches 14.95
out. At 3 days it was not yet steady: levels held, but storage was still
rising by about 1.9 m³/s.

**What the steady test shows about the terrain:** 0.85 km² is wet at
15 m³/s, a flow SP Águas' rating keeps inside the channel. Much of it is
low ANADEM ground beside the river (about half the raw bank values lie
below the fitted bank) filling up over about 9 days. This is the
ground-height limitation the design warned of, and it will appear in the
scores as modelled water that the radar does not see.

**Consequence for the flood runs:** "from a steady state at that hour's
flows" needs about 10 days of warm-up at the starting flows before the
72-hour run. That is about 100 seconds of computing per pass.

### Channel roughness calibration (done)

`pipeline/flood_lisflood_build.py calibrate`, 39 steady runs of 10 days
(13 values of n × 15, 10 and 5 m³/s); results in
`models/flood_run1/lisflood/calibration.json` and
`data/logs/flood_lisflood_calibration.log`. Targets on the gauge scale at
3E-063, from SP Águas' rating: 1.57, 2.15 and 2.71 m.

| Channel n | Error at 5 / 10 / 15 m³/s | RMSE |
| --- | --- | --- |
| **0.020 (chosen)** | +0.21 / −0.01 / −0.25 m | **0.189 m** |
| 0.025 | +0.31 / +0.15 / −0.04 m | 0.201 m |
| 0.030 | +0.41 / +0.30 / +0.16 m | 0.307 m |
| 0.035 | +0.49 / +0.45 / +0.33 m | 0.430 m |
| 0.050 | +0.74 / +0.81 / +0.63 m | 0.729 m |
| 0.080 | +1.17 / +1.21 / +0.96 m | 1.117 m |

- **n = 0.020, the lowest value in the range**, by the design's rule (lowest
  RMSE). The minimum is bracketed: at 0.020 the errors already change sign
  across the three flows, and 0.025 is only slightly worse. A lower n would
  pull the 15 m³/s error further down. So the edge of the range is not
  hiding a much better fit.
- **0.020 is low for a natural channel.** It is an effective value. It makes
  up for the model's channel path being 28% longer than the river's
  (staircase cells), which flattens the slope the model sees.
- **The model's stage–discharge curve is flatter than the rating.** From 5
  to 15 m³/s the gauge rises 0.68 m in the model against 1.14 m in the
  rating. At low flows the model's level is too high, plausibly because the
  downstream level (the plant's pond, through the datum tie) backs water up
  to the gauge. At 15 m³/s it is too low. No single n fixes the shape.
- At 15 m³/s with n = 0.020 the river stays in its channel at the gauge
  (2.46 m against the 3.01 m overflow level).
- Some high-n runs were still filling floodplain hollows after 10 days
  (outflow below inflow at 10 m³/s). The gauge level had settled in all
  of them (≤ 0.5 cm change in the last 2 hours).

### Scoring mask and terrain-only benchmark (done)

`pipeline/flood_benchmark.py`; outputs `data/processed/flood_run1_scoring_mask.tif`,
`flood_run1_benchmark.tif` (one band per scored pass), `flood_run1_benchmark.json`;
quick look `docs/flood_run1_benchmark.png`. Made before any radar map or model
output existed.

- **Scoring grid** (an implementation detail): EPSG:32723, 10 m cells on
  multiples of 10 m. That is the grid of the terrain-corrected radar scenes
  (324 of 330 orbit-53 entries; the rest will be resampled by nearest
  neighbour). Size 521 × 443.
- **Scoring mask:** of the 8.69 km² domain, **1.64 km² (19%) is scored**
  open ground. The exclusions overlap: building footprints plus 20 m cover
  3.67 km², tree cover 3.52, built-up land 3.12, the channel strip 0.38 and
  slopes over 10° 0.33.
- **Benchmark:** H (height above the river of the bank cells beside 3E-063,
  the lower side) is 1.51 m. So a cell is wet if its height above the river
  is at most stage − 1.50 m.
- **The benchmark floods about 60% of the scored ground at every pass**
  (0.98–1.02 km² of 1.64), and 3.75–4.03 km² of the domain. It barely
  changes between the smallest flood (3.24 m) and the largest (3.59 m). The
  valley floor is flat in ANADEM and lies within about 2 m of the river
  line, 22% of it below the line itself, which ANADEM does not resolve. A
  terrain-only map therefore cannot tell a small flood from a large one
  here. Whether that makes it easy or hard to beat depends on how much
  water the radar shows. That is unknown, and must stay unknown until the
  radar maps are made by their fixed rule.

### Observed flood maps and the data gate: **failed; run 1 stops**

`pipeline/flood_radar_maps.py`; outputs `data/processed/flood_run1_observed.tif`
and `flood_run1_observed.json`; quick look `docs/flood_run1_observed.png`. Made
by the design's rule before any modelled flood map existed (none exists).

- **What was read:** 124 radar scene windows (the 13 passes and their dry
  references) from `sentinel-1-rtc`, VV, logged in the manifest without the
  access token. The windows are cached outside git.
- **Implementation fix, made after the first result and before any
  interpretation:** each pass over Atibaia comes as two adjacent slices
  (frames). The first run used one slice per pass, which left
  25 February 2016 with radar data on 4.7% of the scored ground. It also
  counted each slice of a reference date as a reference. A pass is now the
  mosaic of its slices, and references are counted by date. The rule is
  unchanged, and only 25 February 2016's count changed (2 → 123 pixels,
  now with full coverage).
- **Result:** at every pass the rule finds **102–360 flooded pixels
  (0.010–0.036 km²)** on the 1.64 km² of scored ground, 0.6–2.2% of it.
  No pass reaches the 1,000 pixels (0.1 km²) needed to be scored, so **no
  pass is scored, the data gate cannot be passed, and by the design's own
  rule run 1 stops: there is no model test.** Radar data covered 100% of
  the scored ground at every pass.

| Pass (UTC) | Stage at 3E-063 | Dry references | Flooded pixels on scored ground |
| --- | --- | --- | --- |
| 2016-01-20 08:30 | 327 cm | 8 | 232 |
| 2016-02-25 08:30 | 339 cm | 8 | 123 |
| 2017-01-14 08:30 | 324 cm | 15 | 209 |
| 2017-01-26 08:30 | 346 cm | 15 | 144 |
| 2018-02-02 08:30 | 336 cm | 14 | 295 |
| 2018-03-04 08:30 | 333 cm | 14 | 219 |
| 2019-03-05 08:31 | 345 cm | 14 | 237 |
| 2020-02-28 08:31 | 358 cm | 14 | 131 |
| 2021-01-17 08:31 | 340 cm | 13 | 102 |
| 2024-12-27 08:31 | 326 cm | 6 | 222 |
| 2026-02-02 08:30 | 324 cm | 6 | 298 |
| 2026-02-14 08:30 | 349 cm | 5 | 360 |
| 2026-02-26 08:30 | 324 cm | 4 | 180 |

**What the radar shows (reported, not part of any test):**
- **The scenes are sound.** Backscatter on the scored ground has a median
  of −7 to −9 dB, normal for vegetated land. The flood passes are slightly
  brighter than their references, as wet soil and vegetation are, not
  darker as open water is.
- **Most flagged pixels are noise.** They are isolated pixels spread over
  the whole grid, hillsides outside the domain included. Only a few small
  patches recur in three or more passes: one beside the town gauge, one
  north of the river near 339,800 E, and one at the west end of the domain.
- **No broad open water on the valley floor.** At these stages (0.2–0.6 m
  above SP Águas' overflow level, about 18–35 m³/s), at 05:30 local time,
  the radar sees no open water spread over the open ground of the valley
  floor in this reach.
- **The terrain says otherwise.** The terrain-only benchmark marks about
  60% of the scored ground wet at the same passes. The LISFLOOD-FP steady
  test already wets 0.85 km² at 15 m³/s.

Possible reasons, which the data here cannot separate:
- The floods at these stages may stay close to the channel, under trees or
  in streets, all excluded from scoring.
- Flooded grass and crops brighten in radar and are not open water, so the
  rule misses them.
- The passes are at 05:30, after the hourly peaks in most cases.
- ANADEM may put the valley floor too low relative to the river.

Whatever the mix, a flood model standing on ANADEM here would show far more
open water than the radar does.

**Outcome by the design's rules:** run 1 stops at the data gate. Nothing
modelled is shown, and the observed radar maps are not shown in the viewer
either (the design allows that only once the gate has passed). A different
test, observation or rule would be a new run with its own design. It would
be written knowing these results, so it could not be blind to them.

### What is still missing (17 November 2026)

| Needed for | Item | Status | What unblocks it |
| --- | --- | --- | --- |
| Simulating | Inflow at 3E-063, hourly | Have | – |
| Simulating | Downstream level at 62671200, hourly | Have (13 passes) | – |
| Simulating | Ground heights (ANADEM window) | Have | – |
| Simulating | Tributary inflow points (check 2) | Done: four inside the domain | – |
| Simulating | Channel widths (check 2) | 11 m from OSM (approved after the width rule failed) | – |
| Simulating | Bank and bed profile (check 2) | Done: isotonic bank (approved), bed 2.11 m below | – |
| Simulating | Buildings raised into the 5 m composite | Footprints exist (`web/tools/build_buildings.mjs`) | Nothing; can be done now |
| Simulating | Composite terrain, domain, roughness, height above river | Done (model-independent) | – |
| Simulating | SFINCS model | Set aside: cannot carry the channel | – |
| Simulating | LISFLOOD-FP 8.2 build and smoke test | Done; passes the channel test | – |
| Simulating | LISFLOOD-FP setup and the datum tie | Approved | – |
| Simulating | Real-domain model and steady test (check 5) | Done: steady at 10 days | – |
| Simulating | Channel roughness from the rating | Done: n = 0.020, RMSE 0.19 m | – |
| Testing | Design and addendum committed | Not committed | The project lead's go-ahead |
| Testing | Observed flood maps and the data gate (check 3, second half) | **Done: gate failed (no pass reaches 0.1 km²); run 1 stops** | – |
| Testing | Scoring mask and terrain-only benchmark | Done (1.64 km² scored) | – |
| Testing | 13 passes run, scored, variations | Not started | All of the above |
| Showing | Observed radar flood maps in the viewer | Not started | The data gate passing (no model needed) |
| Showing | Modelled flood extent in the viewer | Allowed only if accepted | Acceptance |

Not obtainable from open data, and so outside run 1: surveyed ground
heights or lidar for the town, river cross-sections, flows on the
tributaries, the plant's pond levels and crest, and discharge measured above
the overflow level. Without them run 1 cannot give depths in streets, or any
flood larger than those tested.

**The tested range is now 324–359 cm at 3E-063**, the stages of the 13
scored passes. With 13 September 2026 dropped, the "321 to 377 cm" in the
outcome rules becomes 324–359 cm: that section already ties the range to
the passes tested.
