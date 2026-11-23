# Lake beds from waterlines (Jaguari-Jacareí, Cachoeira, Atibainha): design and tests, fixed before any image is read

Drafted 23 November 2026. **Status: draft, not approved.** Nothing has been
built. **No image pixel has been downloaded or looked at.** Only catalogue
metadata has been read (scene dates, platforms and scene-wide cloud cover),
and joined with the operator's daily levels to count which levels the
archive covers (below). From approval on, the only additions allowed are the
pre-build addendum, and nothing in this file may change after any test
number has been computed.

## What this is, stated plainly

- The three Cantareira lakes in the viewer's window have no public
  bathymetry. The Copernicus DEM and ANADEM see only their water surface.
  But their levels have swung widely since 1984, and satellites have
  photographed them at many of those levels. **Each image's waterline, at
  the operator's level for that day, is a contour line of the lake bed.**
  Stacking forty years of waterlines maps the bed between the lowest and
  highest levels the images saw.
- **The claim sought:** a bed for each lake, between its lowest and highest
  imaged levels, that (1) holds the operator's stored volume between levels
  and (2) predicts the waterlines of images held out of the mapping.
- **Not claimed, even on a pass:** anything below the lowest imaged level
  (left unknown); bed heights on the DEM's datum beyond the tie's stated
  uncertainty; changes of the bed over time (siltation); lake currents.
- **What it is for:** first, the viewer could draw each lake at its recorded
  level on the replayed date, which the README lists as deliberately absent
  ("Lake extent or depth by date"). Second, it is the bed a later
  LISFLOOD-FP through-flow run would need; that run is not part of this
  design and would need its own.
- **Paiva Castro is left out:** its level moved only 3.3 m in the record,
  which is a few 30 m cells of shore.

## What the archive holds (catalogue metadata only)

Microsoft Planetary Computer STAC, searched 23 November 2026 over the three
lakes: 892 Landsat Collection 2 Level-2 scenes (Landsat 4, 5, 7, 8 and 9)
and 501 Sentinel-2 L2A scenes with scene-wide cloud cover under 60%.
Joining the scenes with scene-wide cloud of 30% or less to the operator's
level on their dates:

| Lake | Level record (m) | Levels on those scenes (m) | Thin parts |
| --- | --- | --- | --- |
| Jaguari-Jacareí | 809.99–844.70 (34.7 m) | 810.08–844.66 | 1–6 scenes per metre below 824 m, none in 824–825 m; the low levels are all 2015 |
| Cachoeira | 811.35–821.45 (10.1 m) | 812.35–821.27 | the lowest metre of the record never imaged |
| Atibainha | 775.13–787.29 (12.2 m) | 775.21–787.18 | 0–6 scenes per metre from 776 to 781 m |

Scene-wide cloud says little about cloud over a lake; the per-lake cloud
rule below decides which scenes are used.

## Data

- **Levels and volumes:** ANA SAR, Cantareira module, daily level (m) and
  stored volume (hm³), already in the pipeline (`fetch_sar_cantareira.py`);
  complete daily from 1984 for the three lakes.
- **Images:** Landsat Collection 2 Level-2 surface reflectance, Tier 1 only
  (30 m; USGS, public domain) and Sentinel-2 L2A (Copernicus, free and
  open), both from Planetary Computer, read as byte ranges of their
  cloud-optimised GeoTIFFs over each lake's window only, with every read
  logged in `data/raw/manifest.jsonl` as for the other sources. Cached
  outside git.
- **Lake region:** each lake's OpenStreetMap outline (relations 452185 and
  7004538, 2906093, 2319460), buffered by 300 m.
- **Datum tie:** Copernicus GLO-30 at 1 arc-second over the three lakes.

## Water maps, fixed rule

- **Grid:** WGS 84 / UTM 23S (EPSG:32723), 30 m, on the Landsat Collection 2
  cell grid (Landsat's own UTM 23N grid shifted by the 10,000 km false
  northing; no resampling of Landsat). Sentinel-2 reflectances are averaged
  onto it by area.
- **Water index:** MNDWI = (green − SWIR1) / (green + SWIR1) on surface
  reflectance (Landsat 4–7 SR_B2 and SR_B5; Landsat 8–9 SR_B3 and SR_B6;
  Sentinel-2 B03 and B11).
- **Valid cells:** not cloud, cloud shadow, dilated cloud, cirrus (high
  confidence), snow, fill or saturated (Landsat `QA_PIXEL`, `QA_RADSAT`);
  Sentinel-2 SCL classes 4, 5, 6 and 7 only (vegetation, bare, water,
  unclassified). Landsat 7's scan-line gaps
  after 31 May 2003 are fill: missing cells, not a reason to drop a scene.
- **Scene used for a lake** if, over the lake region, at least 60% of the
  cells are not fill and no more than 10% of the not-fill cells are cloud or
  shadow. One scene per sensor per day.
- **Wet:** MNDWI above the scene's Otsu threshold over its valid lake-region
  cells, with the threshold clamped to [−0.2, 0.3] (0.0 if Otsu fails).
- **Level of a scene:** the operator's level on the scene's date (Landsat
  passes between about 09:05 and 10:10 local time, Sentinel-2 at about
  10:12, from the catalogue). Scenes on days without a level are dropped.
- **Held out, fixed before any image is read:** every fifth usable scene per
  lake in date order. The list is committed with the scene lists. The
  usable flag needs only the cloud mask, so the held-out set is fixed
  before any water map is made.

## Bed rule, fixed

For each cell, the mapping scenes give pairs (level L, wet or dry). The bed
height z is the height that best separates them, a cell being wet when the
level is above its bed:

- z minimises the count of wet observations with L ≤ z plus dry
  observations with L > z. Where a range of z ties, z is the midpoint
  between the two observed levels that bound it.
- **Below the lowest imaged level:** wet in every observation (at least 5).
  No height; the lake covers the cell at every imaged level.
- **Outside the lake:** dry in every observation.
- **No estimate:** fewer than 10 valid observations, or more than 20% of
  them on the wrong side of z. Filled from neighbours: repeatedly, the
  median z of the cell's estimated neighbours (8-connected), only for cells
  enclosed by estimated ones.
- **The lake at a level L** is the cells with z < L (and the cells below
  the lowest imaged level) that join the cell at the dam through 4-connected
  cells. Farm ponds and puddles inside the buffer are dropped by this rule.

## Datum tie

The operator's levels are not on the DEM's datum (EGM2008). The offset is
the median, over cells with a bed height that the DEM sees as dry ground
(DEM height more than 1 m above the DEM's own flat lake surface), of DEM
height minus z. It is reported with its interquartile range. GLO-30 is a
surface model, so grass on the exposed bed is included; the drawdown zone is
mostly bare or grass. The tie only places the bed under the viewer's
terrain; neither test depends on it.

## Tests, fixed here, per lake

**Operator's volume curve.** V_op(L) is the median of the reported volumes
on days with a level within ±2 cm of L, over the whole record. The
interquartile range at each level is reported, since the operator may have
revised its level–volume table.

**Bed volume.** The volume between two levels is the integral of the lake's
area (as above) over level, on the 30 m grid.

1. **Volume.** Between L_a and L_b, the 5th and 95th percentiles of the
   mapping scenes' levels:
   - total volume change within **±10%** of the operator's;
   - median absolute error over consecutive 2 m bands within **15%**.
2. **Held-out waterlines.** For each held-out scene, the lake the bed
   predicts at that scene's level against the scene's own water map (with
   the same connection rule), over cells valid in that scene:
   - median ratio of predicted to mapped lake area between **0.95 and 1.05**;
   - median accuracy, over cells of the drawdown zone within 5 cells
     (150 m) of the mapped waterline, of at least **0.85**.

**A lake is accepted only if tests 1 and 2 both pass.**

**Reported, not scored:** the area–level curve against the slope of the
operator's volume curve; each test split by sensor (Landsat 4–5, 7, 8–9,
Sentinel-2) and by decade; the share of cells filled from neighbours; the
datum offset and its spread; the cells whose bed rests on fewer than 20
observations.

The thresholds are judgements. Thirty-metre cells along a shore this
dendritic put a few percent of each lake's area in mixed cells, so ±10% on
volume leaves room for that but not for a systematic error such as hill
shadow read as water.

## Pre-build checks (no test number computed)

Recorded in an addendum to this file.

1. Catalogue entries for both collections fetched through the pipeline and
   logged; per lake, the scene list with each scene's level; cloud fraction
   over each lake from the masks only; usable and held-out lists committed.
2. Read check on four non-held-out scenes (Landsat 5, 7 after 2003, 8 and
   Sentinel-2): bands and masks decode; the grid lines up with the OSM
   shore to within one cell; bytes per scene measured. **The full download
   is estimated at 3–5 GB of range reads; if the measured estimate passes
   6 GB, stop and ask.**
3. GLO-30 window over the three lakes fetched and logged.

The water-mapping rule may be corrected only for errors found in checks
1–3, on scenes not held out, before any test number exists. Each correction
goes in the addendum with the scenes that showed it.

## Tooling, needs approval

The per-cell fit runs over about half a million cells and up to 1,400
scenes, too slow in standard-library Python. Reading stays in the
standard-library COG reader (`pipeline/cogread.py`, extended to read
`uint16` multi-band QA where needed). The water maps, the fit and the tests
run in the existing conda environment `atibaia-sar` (numpy, rasterio, scipy;
`envs/flood-sar.yml`), which needs nothing new installed.

## Outcome rules

- **Accepted.** The lake's bed is published to
  `web/public/data/lake_beds.json` (heights on the operator's datum, the
  offset, the lowest and highest imaged levels). The viewer may then draw
  that lake at its recorded level on the replayed date: the terrain inside
  the lake follows the bed, and the water surface is the lake at that
  level. Label: **"Lake at the recorded level. Bed mapped from
  Landsat and Sentinel-2 waterlines 1984–2026; below [lowest imaged level]
  unknown."** On days below the lowest imaged level, the lake is drawn at
  its lowest imaged extent and the label says the lake was lower than any
  image shows. Exposed bed takes a display colour, since the basemap
  imagery shows water there. `tests/test_pipeline.py` is extended so that
  no bed reaches the viewer without an accepted test file.
- **Not accepted.** Nothing changes in the viewer; the lakes keep their
  fixed outlines. The result goes in the README. No re-tuning: a revised
  rule is a new design.
- **Either way**, the water maps are data and may be kept for other uses.

## Expectation, written before the build

- **Jaguari-Jacareí** should pass: its 35 m range is imaged from top to
  bottom. Its lowest 14 m rest on few scenes, all from the 2014–15 crisis,
  so that part of the bed is coarse.
- **Cachoeira** should pass, over the 9 m imaged.
- **Atibainha** is the most at risk: from 776 to 781 m it rests on a
  handful of scenes, so the bed there is coarse and the band test could
  fail.
- The likeliest systematic errors: hill shadow on steep shores read as
  water (beds too high); floating plants, turbid shallows and wet mud near
  the waterline (either way); a level–volume table drawn from an old survey
  while the lakes have silted (volumes off in one direction).

## What this design does not fix

- The bed below the lowest imaged level. A LISFLOOD-FP run would need a rule
  for it; the operator's volume below that level bounds it but does not
  shape it.
- Siltation since 1984: the bed is a composite of forty years.
- The resolution: 30 m cells blur a shore that moves a few metres per metre
  of level on steep slopes.
- The time of the operator's daily reading is not published; levels move a
  few centimetres a day, small against a 30 m cell.
- Lake currents. Wind and layering drive most of them; nothing here
  addresses either.
