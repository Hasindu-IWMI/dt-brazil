# Inflow model, run 3: design and test, fixed before any run

Written 14 November 2026, before any code for run 3 exists. Nothing in this
file may be changed after run 3 starts; a change means a run 4 with its own
file.

## Why a new design

Runs 1 and 2 calibrated GR4J on a wet decade (2004–2013) and tested it on
other periods. Both failed. The investigation
(`runoff_shift_investigation.md`) showed why: the share of rain that becomes
inflow fell from about 0.32 to about 0.19 in 2014–2016, confirmed by an area
measured only by river gauges. Climate explains most of that drop and
catchment memory may explain some of the rest. A model tuned only on wet
years cannot be trusted in a drought.

## What is honest to claim

Every period in the record has now been looked at twice. No run on this record
is a blind test any more. Run 3 therefore tests a narrower claim, **robustness
across climate regimes**, and adds two checks on data no model has touched.

## The question

Can one model structure, with one parameter set per catchment, reproduce
inflow in a regime it was not calibrated on, in both directions (wet to dry
and dry to wet)?

## Design: two-way differential split-sample (Klemeš 1986)

| Fold | Calibrate on | Validate on | What it tests |
| --- | --- | --- | --- |
| 1 | 2004–2013 (wetter regime) | 2014 to the last day with rain data (drier regime) | Wet to dry |
| 2 | 2014 to the last day with rain data | 2004–2013 | Dry to wet |
| Early check | parameters from each fold | 1986–2001 | Reported for both catchments; pass/fail for Cachoeira only |

Warm-up: two years before each calibration or validation window, not scored.

Atibainha's 1986–2001 inflow record is excluded from pass/fail because the
investigation found it doubtful on independent evidence (runoff share a third
above the climate estimate; implied reservoir capacity 130 hm³ then against
96 hm³ now). It is still reported.

## Candidate models

| Model | Parameters | Why it is a candidate |
| --- | --- | --- |
| GR4J | 4 | The baseline from runs 1 and 2; tells us whether calibration period alone was the problem |
| GR5J (Le Moine 2008) | 5 | Adds a threshold to the groundwater exchange, so the catchment can lose water when its stores are low and gain when they are high. This is the smallest change that lets runoff share depend on catchment state |

No other structure will be tried in run 3.

**Parsimony rule.** GR5J is preferred over GR4J only if it passes a test that
GR4J fails, or if its mean validation KGE across both folds and both
catchments is higher by at least 0.05. Otherwise GR4J is kept.

## Changes from runs 1 and 2, all fixed here

| Item | Runs 1–2 | Run 3 | Reason |
| --- | --- | --- | --- |
| Rainfall | Run 2: audited | Audited, unchanged | – |
| Objective | KGE of daily flow | KGE of the square root of daily flow | Daily KGE is dominated by floods; low flows were overestimated two- to fourfold |
| Days with observed inflow at or below zero | Included | Excluded from objective and metrics, and counted | They are artefacts of the operator's balance |
| Upper bound of x1 | 2,500 mm | 5,000 mm | Atibainha sat on the bound in both runs |
| Bounds of x5 (GR5J only) | – | −1 to 2 (dimensionless) | Range used in the literature for the exchange threshold |
| Search | 1,500 random + 500 refinement | 3,000 random + 1,000 refinement | Five parameters need a wider search |
| Rain-day alignment | Chosen on calibration | Chosen on calibration, per fold | Unchanged |
| Random seed | 20261114 | 20261114 | Unchanged |

## Acceptance, fixed here

A model structure is **accepted for a catchment** only if, in the validation
window of **both** folds:

1. Daily KGE (untransformed flow) is at least 0.50 and above the calendar-day
   benchmark built from that fold's calibration window.
2. Total volume bias is within ±25%.
3. Monthly-mean KGE is at least 0.60. Reservoir decisions depend on monthly
   volumes, and the daily record is noisy.
4. Low-flow bias is within ±50%: the mean of modelled flow on the days when
   observed flow is in its lowest fifth, against the observed mean on those
   days.

Criteria 1 and 2 are unchanged from runs 1 and 2. Criteria 3 and 4 are new and
make the test harder, not easier. For Cachoeira the same four criteria must
also hold on 1986–2001 using each fold's parameters.

If a structure is accepted, its final parameters come from one calibration on
2004 to the end of the record, and only then may modelled inflow appear in the
viewer, labelled with these results.

## Two checks on untouched data (reported, not pass/fail)

1. **Proxy-basin transfer.** Each accepted parameter set is run, without any
   re-tuning, on the independent 351 km² area between the dams and the Atibaia
   gauge, and compared with its gauge-derived daily flow. No model has been
   fitted to this area.
2. **Forward test.** The accepted model is frozen. As inflow records after the
   last day used here become available, they are compared with what the frozen
   model gives. This is the only truly blind test available.

## What is written down as expected, before the run

- GR4J will pass fold 2 for the wet decade's volume but overestimate drought
  volume in fold 1, as before.
- GR5J should cut the drought bias at Cachoeira. Whether it passes the
  low-flow criterion is uncertain.
- Atibainha may fail on 2017 onward in fold 1 regardless of structure, because
  its rainfall there is probably still too low.

## What a failure would mean

If neither structure is accepted, the conclusion is that daily inflow in
these catchments cannot yet be modelled defensibly from open rain gauges and
reanalysis temperature. The pilot would then stay an observed-record tool
until better rainfall (CEMADEN, state network) or operator data are obtained.
That is an acceptable result.

## Known weaknesses this design does not fix

- Evaporation demand still comes from reanalysis temperature.
- Rain coverage is thin after 2022 (one gauge or none on many days at
  Cachoeira).
- The target itself, operator-computed inflow, has no published uncertainty.
- Uncertainty in the result will again be reported from parameter spread only,
  which runs 1 and 2 showed to be uninformative. A better treatment (rainfall
  ensembles) is left for later.
