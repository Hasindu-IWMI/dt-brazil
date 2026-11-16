# Inflow model: calibration and validation

Generated 2026-11-14 12:10 UTC by `pipeline/model.py`. The test design is fixed in that file's header and was written before the first run.

**This is run 2.** The only change from run 1 is the rainfall input, now audited by `pipeline/audit_rain.py`. The test is unchanged. The validation periods were seen once in run 1, so this is not a blind test. Run 1 is archived as `model_validation_report_run1_unaudited.md`.

Model: GR4J, daily, four parameters. Target: natural inflow reported by ANA SAR. Acceptance in every validation period: KGE above the calendar-day benchmark, KGE >= 0.50, volume bias within 25%.

## Cachoeira (392 km2)

**Verdict: NOT ACCEPTED: failed at least one validation period.**

- Parameters: x1 = 1637.2 mm, x2 = -0.33 mm/day, x3 = 64.5 mm, x4 = 1.13 days.
- Rain alignment chosen on the calibration period: rain labelled D used on D (calibration KGE 0.811; the other alignment gave 0.809).
- Parameter ensemble: best 30 sets, calibration KGE 0.811 to 0.811.
- Days from 1984 with no rain gauge reporting (rain taken as 0): 0.

| Period | Days | KGE | Benchmark KGE | Correlation | Variability ratio | Volume bias | NSE | Low-flow error | Observed inside ensemble | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| calibration_2004_2013 | 3653 | 0.81 | 0.36 | 0.81 | 1.00 | +1% | 0.62 | +208% | 1% | calibration |
| A_drought_2014_2016 | 1096 | 0.61 | 0.02 | 0.84 | 1.19 | +30% | 0.52 | +401% | 1% | NO |
| B_recent_2017_on | 3499 | 0.75 | 0.27 | 0.76 | 1.00 | +7% | 0.52 | +362% | 1% | yes |
| C_early_1986_2001 | 5844 | 0.67 | 0.24 | 0.83 | 1.26 | +12% | 0.49 | +188% | 1% | yes |

## Atibainha (312 km2)

**Verdict: NOT ACCEPTED: failed at least one validation period.**

- Parameters: x1 = 2500.0 mm, x2 = -0.29 mm/day, x3 = 22.0 mm, x4 = 2.36 days.
- Rain alignment chosen on the calibration period: rain labelled D used on D - 1 (calibration KGE 0.702; the other alignment gave 0.701).
- Parameter ensemble: best 30 sets, calibration KGE 0.702 to 0.702.
- Days from 1984 with no rain gauge reporting (rain taken as 0): 7.

| Period | Days | KGE | Benchmark KGE | Correlation | Variability ratio | Volume bias | NSE | Low-flow error | Observed inside ensemble | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| calibration_2004_2013 | 3653 | 0.70 | 0.23 | 0.70 | 1.02 | -1% | 0.39 | +196% | 1% | calibration |
| A_drought_2014_2016 | 1096 | 0.74 | -0.24 | 0.81 | 1.09 | +14% | 0.56 | +374% | 1% | yes |
| B_recent_2017_on | 3499 | 0.35 | 0.03 | 0.57 | 0.63 | -31% | 0.26 | +254% | 1% | NO |
| C_early_1986_2001 | 5844 | 0.44 | 0.04 | 0.69 | 0.66 | -32% | 0.36 | +256% | 1% | NO |

## How to read this

- KGE is 1 for a perfect match. The benchmark column is a model that only knows the average seasonal cycle; a rainfall-runoff model is worth having only where it beats that.
- Variability ratio below 1 means the model is too smooth; volume bias is total modelled over observed volume.
- Low-flow error is the error in the mean of the driest tenth of observed days.
- The ensemble spread covers parameter uncertainty only. A low share of observations inside it means the errors come from elsewhere: rainfall sampling, evaporation, the inflow record, or the model structure.
- The inflow record is itself computed by the operator from a reservoir balance and contains negative days.
