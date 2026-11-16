# Upper Atibaia water-security pilot

First increment of the Brazil river-basin digital twin, for the upper Atibaia
sub-basin of the Cantareira / PCJ system (São Paulo). It is built on open data
only and currently does one thing: **replay observed daily records in 3D, with
a small set of clearly labelled derived diagnostics.**

It is not a digital twin. Inflow models were built and tested four times and
none passed validation, so nothing modelled is shown; there is no forecast and
no live feed.
See "What is and is not here" below.

## Run it

```bash
npm --prefix web install
```

```bash
npm --prefix web run dev
```

Then open http://localhost:5173. Drag to orbit, scroll to zoom, use the slider
or Play to move through time, click the chart to jump to a date.

## Refresh the data

Python 3.10+ with the standard library only; Node 20+.

```bash
python -I pipeline/fetch_sar_cantareira.py 1982 2026
```

```bash
python -I pipeline/fetch_ana_series.py 3 62670000 62665000 62662000 62676000 62678150 62669900 62680000 62690000 62665100
```

```bash
python -I pipeline/process.py
```

```bash
npm --prefix web run scene
```

The reservoir service is slow and times out; the fetch is resumable, so run it
again until it reports nothing new. Every download is logged with URL, size and
SHA-256 in `data/raw/manifest.jsonl`.

## Layout

| Path | Contents |
| --- | --- |
| `pipeline/` | Acquisition and processing scripts (Python, standard library) |
| `data/raw/` | Downloads exactly as received, plus the manifest |
| `data/processed/` | Tidy CSVs: one per reservoir and gauge, system totals, control point |
| `docs/` | Generated reports: data quality, forcing, model validation |
| `web/` | Three.js viewer (Vite). `web/public/data/` holds what it reads |

## Sources

| Data | Source | Type | Licence / terms |
| --- | --- | --- | --- |
| Reservoir level, storage, inflow, release (daily) | ANA SAR, Cantareira module | Observed, operator-reported | None shown on the page |
| River discharge (daily) | ANA HidroSerieHistorica web service | Observed stage, rating-curve discharge | Not stated |
| Terrain | Copernicus DEM GLO-30 (ESA) | Satellite surface model, EGM2008 | Free with attribution |
| Lake outlines, rivers | OpenStreetMap via Overpass | Mapped | ODbL 1.0 |
| Operating bands | Joint Resolution ANA/DAEE 925/2017, as tabulated by Comitês PCJ | Regulation | Public |

## What is and is not here

Observed and shown as-is: reservoir level, useful volume, inflow and release;
river flow at four gauges. Gaps are shown as "no data" and never filled.

Derived, and labelled as derived on screen:

- System storage = sum of the four reservoirs, as % of 981.56 hm³.
- Operating band = the band whose threshold that percentage meets (shown only
  from June 2017, when the rules took effect).
- Implied net export = total inflow − total release − storage change. A
  residual that lumps the withdrawal to São Paulo with transfers received,
  evaporation and measurement error. It is not a measurement.
- Local inflow = flow at the Atibaia gauge − releases from Cachoeira and
  Atibainha, same day.

Deliberately absent, because the open data cannot support it:

- **Lake extent or depth by date.** No bathymetry is public, so lake outlines
  are fixed map outlines and storage is shown by colour and a column.
- **Tunnel flows and the withdrawal to São Paulo.** Not published.
- **Sub-daily data.** ANA's public telemetry returns nothing for these gauges.
- **Any simulated or forecast value.** The first inflow model failed
  validation (see below) and is withheld from the viewer.
- **Restoration or land-use effects.** No defensible basis yet.

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
- **Gauge below release.** The Piracaia gauge reads more than 0.5 m³/s below
  the Cachoeira release on about 100 days a year in 2017, 2018 and 2022. A
  one- or two-day shift does not fix it. Needs the operator's measured outflow
  or the gauge's rating history.
- **Capacities before 2000 differ a lot** (Atibainha 130 hm³, Paiva Castro
  27.6 hm³, against 96.25 and 7.61 today). Volumes across revisions are not
  strictly comparable; long-term storage trends should be read with care.
- **Jaguari-Jacareí shows about 599 hm³ capacity for Jan–Aug 2004**, between
  two periods at about 808. Unexplained.
- **The Atibaia gauge record ends on 31 May 2026**; other mid-river gauges end
  in 2022. Ten-minute state telemetry exists but was not downloaded.
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
record: Cachoeira has one gauge or none on 775 days in 2022–2025.

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

## Next steps

1. Send the data requests drafted in `docs/data_requests.md` (six letters in
   Portuguese with English summaries; drafted, not sent). They need a
   Brazilian partner to send or co-sign, and a native speaker's review.
2. Find more rain gauges for 2022 onward (CEMADEN's network has data from 2014).
3. Ask the operator how inflow was computed before 2000 (Atibainha looks too high).
4. Request tunnel-flow, abstraction and measured-outflow data from Sabesp and
   Agência PCJ.
5. Replace the terrain with ANADEM (bare earth) when a 2 GB download is
   acceptable.
