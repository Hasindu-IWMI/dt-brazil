# Inflow model: calibration and validation

Generated 2026-11-14 11:50 UTC by `pipeline/model.py`. The test design is fixed in that file's header and was written before the first run.

Model: GR4J, daily, four parameters. Target: natural inflow reported by ANA SAR. Acceptance in every validation period: KGE above the calendar-day benchmark, KGE >= 0.50, volume bias within 25%.

## Cachoeira (392 km2)

**Verdict: NOT ACCEPTED: failed at least one validation period.**

- Parameters: x1 = 1715.1 mm, x2 = -0.17 mm/day, x3 = 60.4 mm, x4 = 1.13 days.
- Rain alignment chosen on the calibration period: rain labelled D used on D (calibration KGE 0.794; the other alignment gave 0.792).
- Parameter ensemble: best 30 sets, calibration KGE 0.794 to 0.794.
- Days from 1984 with no rain gauge reporting (rain taken as 0): 0.

| Period | Days | KGE | Benchmark KGE | Correlation | Variability ratio | Volume bias | NSE | Low-flow error | Observed inside ensemble | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| calibration_2004_2013 | 3653 | 0.79 | 0.36 | 0.79 | 1.00 | +0% | 0.59 | +208% | 1% | calibration |
| A_drought_2014_2016 | 1096 | 0.57 | 0.02 | 0.85 | 1.18 | +36% | 0.52 | +450% | 1% | NO |
| B_recent_2017_on | 3499 | 0.75 | 0.27 | 0.76 | 1.00 | +8% | 0.51 | +388% | 1% | yes |
| C_early_1986_2001 | 5844 | 0.68 | 0.24 | 0.83 | 1.24 | +13% | 0.50 | +198% | 1% | yes |

## Atibainha (312 km2)

**Verdict: NOT ACCEPTED: failed at least one validation period.**

- Parameters: x1 = 2500.0 mm, x2 = -0.37 mm/day, x3 = 42.2 mm, x4 = 2.37 days.
- Rain alignment chosen on the calibration period: rain labelled D used on D - 1 (calibration KGE 0.595; the other alignment gave 0.590).
- Parameter ensemble: best 30 sets, calibration KGE 0.595 to 0.595.
- Days from 1984 with no rain gauge reporting (rain taken as 0): 1.

| Period | Days | KGE | Benchmark KGE | Correlation | Variability ratio | Volume bias | NSE | Low-flow error | Observed inside ensemble | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| calibration_2004_2013 | 3653 | 0.59 | 0.23 | 0.61 | 1.11 | -5% | 0.13 | +198% | 0% | calibration |
| A_drought_2014_2016 | 1096 | 0.54 | -0.24 | 0.63 | 0.77 | +14% | 0.36 | +798% | 0% | yes |
| B_recent_2017_on | 3499 | 0.08 | 0.03 | 0.52 | 0.42 | -53% | 0.08 | +130% | 0% | NO |
| C_early_1986_2001 | 5844 | 0.39 | 0.04 | 0.65 | 0.61 | -31% | 0.31 | +280% | 0% | NO |

## How to read this

- KGE is 1 for a perfect match. The benchmark column is a model that only knows the average seasonal cycle; a rainfall-runoff model is worth having only where it beats that.
- Variability ratio below 1 means the model is too smooth; volume bias is total modelled over observed volume.
- Low-flow error is the error in the mean of the driest tenth of observed days.
- The ensemble spread covers parameter uncertainty only. A low share of observations inside it means the errors come from elsewhere: rainfall sampling, evaporation, the inflow record, or the model structure.
- The inflow record is itself computed by the operator from a reservoir balance and contains negative days.
