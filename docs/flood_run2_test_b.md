# Flood run 2: test B and the verdict (18 November 2026)

Run 2's design (`docs/model_design_flood_run2.md`) is closed to edits: test B
reports a match against run 1's observed maps, and the design allows no change
after any modelled map has been compared with an observed one. Its result is
recorded here instead.

**Run 2 is closed and not accepted.** The data gate failed (pre-run check 6),
so there was no extent test. Test B, run as information, also failed. The
verdict file says `"passed": false`, and nothing modelled is shown.

## What was run

`pipeline/flood_run2_build.py morning` (log `data/logs/flood_run2_events_morning.log`;
records in `data/processed/flood_run2_events_morning.json`). It ran after the
evening maps and gate were committed (`3d8f8b1`), as the design requires, and
checks for that commit before running.

- **Events:** the 13 morning passes scored in run 1, central run only. The
  design's variations apply to scored events, and with no extent test there
  are none.
- **Two-stage start (change 1):** each event starts at the last hour before
  the pass that 3E-063 stood below 301 cm (0.4 to 9.7 days before). Stage 1
  holds that hour's flows for 10 days with the floodplain closed; every
  stage 1 ended steady (0.0 cm change in its last 2 hours). Stage 2 starts
  from those channel depths on the run 2 ground and runs hourly to an hour
  after the pass.
- **Implementation details, fixed in the script before any run:**
  - The pass's output is the hourly output nearest the middle of the
    scene's acquisition: 09:00 UTC for all 13. The middles fall between
    08:30:00 and 08:31:30. Three fall exactly on 08:30:00, half-way between
    outputs, and the script rounds those up.
  - Mapped permanent water starts full to its spill level: 131 of its 154
    cells hold water at the start (0.052 km², median 1.93 m deep); the
    other 23 spill freely.
  - The dam releases in the tributary rule are taken for the local day
    (UTC−3) of each hour.
  - Every event's boundary records were complete but for 2 bridged hours
    of the 62671200 level.
- **Mass balance:** the largest volume error in any event was 6 × 10⁻¹⁵ of
  its peak volume.
- **A fault in the script, fixed without re-running any model:** the step
  that writes each event's record stopped on a number type JSON cannot
  store. All 13 model runs had finished and saved their outputs. The records
  were rebuilt from those outputs (`flood_run2_build.py summarise`).

## Test B

`pipeline/flood_run2_score.py` (`data/processed/flood_run2_test_b.json`,
figure `docs/flood_run2_test_b.png`). Deep water is modelled water at least
0.5 m deep on run 2's scoring mask (15,893 cells of 10 m; run 1's open ground
less mapped permanent water), at the output nearest the pass. The depth is
LISFLOOD-FP's `.wdfp`, taken from the 20 m grid by nearest neighbour.

| Pass (UTC) | Stage at 3E-063 | Deep water (≥ 0.5 m) | Wet (> 10 cm) | Gauge level, model / record | CSI against run 1's map |
| --- | --- | --- | --- | --- | --- |
| 2016-01-20 08:30 | 327 cm | 0.280 km² | 0.554 km² | 2.85 / 3.27 m | 0.012 |
| 2016-02-25 08:30 | 339 cm | 0.204 km² | 0.529 km² | 3.00 / 3.39 m | 0.007 |
| 2017-01-14 08:30 | 324 cm | 0.072 km² | 0.305 km² | 2.80 / 3.24 m | 0.016 |
| 2017-01-26 08:30 | 346 cm | 0.222 km² | 0.664 km² | 3.09 / 3.46 m | 0.014 |
| 2018-02-02 08:30 | 336 cm | 0.181 km² | 0.511 km² | 3.02 / 3.37 m | 0.022 |
| 2018-03-04 08:30 | 333 cm | 0.092 km² | 0.400 km² | 3.00 / 3.33 m | 0.012 |
| 2019-03-05 08:31 | 345 cm | 0.203 km² | 0.651 km² | 3.08 / 3.45 m | 0.019 |
| 2020-02-28 08:31 | 359 cm | 0.357 km² | 0.745 km² | 3.24 / 3.59 m | 0.008 |
| 2021-01-17 08:31 | 340 cm | 0.203 km² | 0.634 km² | 3.02 / 3.40 m | 0.008 |
| 2024-12-27 08:31 | 326 cm | 0.133 km² | 0.285 km² | 2.75 / 3.26 m | 0.045 |
| 2026-02-02 08:30 | 325 cm | 0.092 km² | 0.303 km² | 2.71 / 3.25 m | 0.011 |
| 2026-02-14 08:30 | 350 cm | 0.361 km² | 0.688 km² | 3.07 / 3.50 m | 0.015 |
| 2026-02-26 08:30 | 324 cm | 0.143 km² | 0.234 km² | 2.70 / 3.25 m | 0.010 |

- **Test B failed.** The median deep-water area is **0.203 km²** against at
  most 0.10 km², and **7** of the 13 floods exceed 0.20 km² against at most 2.
- **Reported:** the median area wet over 10 cm is 0.53 km², a third of the
  scored ground. The median CSI against run 1's morning maps is 0.012. Those
  maps sit about 43 m west of the model grid (check 4), which lowers the
  CSI, but they flag only 0.010 to 0.036 km² at any pass, so no shift would
  bring it near a match.

**The model's river is too low at the gauge, and its floodplain still too
wet.** At every pass the modelled level at 3E-063 is 0.33 to 0.55 m below the
record. That continues the flatter stage–discharge curve found in calibration
(−0.25 m at 15 m³/s); the passes carry 18 to 31 m³/s. So the deep water does
not come from a river set too high.

**Where the deep water stands** (a diagnostic, not part of the design;
script kept outside the repository, method here). Each 20 m cell was classed
on the run 2 ground: inside a closed hollow still left after change 3 (the 10
deep hollows it kept, and pockets closed off by cells raised as buildings), on
ground below the bank of its nearest channel cell, or neither.

- Across the 13 floods, **57%** of the deep scored cells lie in those closed
  hollows (median 72% per flood), 35% on ground between the ordinary river
  level and the bank, and 8% elsewhere.
- 0.07 km² of hollow holds deep water at every pass, even the smallest
  flood.

This is the reading the design wrote down before the run: ANADEM's valley
floor is still too low in places, and better ground heights, not model
settings, are what would change the result.

## The verdict

`data/processed/flood_run2_verdict.json`, written once on 18 November 2026
at 12:04 UTC by the scoring script, which refuses to overwrite it.
SHA-256 `e2f13a03ffbf775ddff21db43235c3a747105eb1e23e87cbbefb48bd2de6756d`.

- `"passed": false`.
- `gate`: as check 6 (G1 0 of 4, G2 0.08).
- `test_a`: null, since the failed gate means there is no extent test.
- `test_b`: the result above.
- `tested_stage_cm`: null, since no extent was tested.

`pipeline/flood_water_viewer.py` publishes nothing without a verdict that says
`"passed": true`, so the viewer shows no modelled water. Any further flood run
is a new design, written knowing these results.
