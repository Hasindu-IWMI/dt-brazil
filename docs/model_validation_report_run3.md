# Inflow model, run 3: results

Generated 2026-11-14 13:18 UTC by `pipeline/model_run3.py`. Design and acceptance test: `model_design_run3.md`, fixed and approved before the run. This was not a blind test: every period had been examined in runs 1 and 2.

Criteria in each validation window: daily KGE >= 0.50 and above the benchmark; volume bias within 25%; monthly KGE >= 0.60; low-flow bias within 50%.

## Cachoeira (392 km2)

### GR4J

| Window | Days | Daily KGE | Benchmark | Volume bias | Monthly KGE | Low-flow bias | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fold1 calibration 2004 to 2013 | 3653 | 0.75 | 0.36 | +1% | 0.80 | +128% | calibration |
| fold1 VALIDATION 2014 to 2026 | 4595 | 0.66 | 0.22 | +12% | 0.66 | +158% | NO: low-flow bias |
| fold1 parameters on 1986 to 2001 (scored) | 5823 | 0.50 | 0.24 | +12% | 0.51 | +79% | NO: daily KGE, monthly KGE, low-flow bias |
| fold2 calibration 2014 to 2026 | 4595 | 0.72 | 0.38 | +1% | 0.80 | +132% | calibration |
| fold2 VALIDATION 2004 to 2013 | 3653 | 0.75 | 0.13 | -8% | 0.85 | +104% | NO: low-flow bias |
| fold2 parameters on 1986 to 2001 (scored) | 5823 | 0.57 | 0.06 | +2% | 0.66 | +61% | NO: low-flow bias |

**GR4J for Cachoeira: fails.**

- fold1: x1 = 1196.5483, x2 = -0.2481, x3 = 57.5734, x4 = 1.1307; rain lag 0; excluded non-positive days in validation: 0
- fold2: x1 = 1356.66, x2 = -0.5873, x3 = 40.2069, x4 = 2.1317; rain lag 1; excluded non-positive days in validation: 0

### GR5J

| Window | Days | Daily KGE | Benchmark | Volume bias | Monthly KGE | Low-flow bias | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fold1 calibration 2004 to 2013 | 3653 | 0.75 | 0.36 | +1% | 0.80 | +128% | calibration |
| fold1 VALIDATION 2014 to 2026 | 4595 | 0.66 | 0.22 | +12% | 0.67 | +157% | NO: low-flow bias |
| fold1 parameters on 1986 to 2001 (scored) | 5823 | 0.50 | 0.24 | +12% | 0.51 | +79% | NO: daily KGE, monthly KGE, low-flow bias |
| fold2 calibration 2014 to 2026 | 4595 | 0.73 | 0.38 | +2% | 0.80 | +130% | calibration |
| fold2 VALIDATION 2004 to 2013 | 3653 | 0.75 | 0.13 | -7% | 0.86 | +109% | NO: low-flow bias |
| fold2 parameters on 1986 to 2001 (scored) | 5823 | 0.58 | 0.06 | +5% | 0.66 | +68% | NO: low-flow bias |

**GR5J for Cachoeira: fails.**

- fold1: x1 = 1223.9325, x2 = -0.1647, x3 = 58.6779, x4 = 1.1218, x5 = 0.3341; rain lag 0; excluded non-positive days in validation: 0
- fold2: x1 = 1593.6329, x2 = -0.1888, x3 = 39.2415, x4 = 2.1005, x5 = 0.0616; rain lag 1; excluded non-positive days in validation: 0

## Atibainha (312 km2)

### GR4J

| Window | Days | Daily KGE | Benchmark | Volume bias | Monthly KGE | Low-flow bias | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fold1 calibration 2004 to 2013 | 3653 | 0.67 | 0.23 | -0% | 0.69 | +151% | calibration |
| fold1 VALIDATION 2014 to 2026 | 4595 | 0.55 | -0.02 | -22% | 0.61 | +139% | NO: low-flow bias |
| fold1 parameters on 1986 to 2001 (reported only) | 5807 | 0.52 | 0.05 | -33% | 0.56 | +22% | not scored |
| fold2 calibration 2014 to 2026 | 4595 | 0.57 | 0.25 | +2% | 0.62 | +160% | calibration |
| fold2 VALIDATION 2004 to 2013 | 3653 | 0.29 | -0.03 | +22% | 0.28 | +174% | NO: daily KGE, monthly KGE, low-flow bias |
| fold2 parameters on 1986 to 2001 (reported only) | 5807 | 0.63 | -0.09 | -16% | 0.73 | +34% | not scored |

**GR4J for Atibainha: fails.**

- fold1: x1 = 2235.4318, x2 = -0.1754, x3 = 10.8429, x4 = 2.3714; rain lag 1; excluded non-positive days in validation: 0
- fold2: x1 = 1238.3195, x2 = 0.1684, x3 = 5.0, x4 = 1.1616; rain lag 0; excluded non-positive days in validation: 0; AT BOUND: x3

### GR5J

| Window | Days | Daily KGE | Benchmark | Volume bias | Monthly KGE | Low-flow bias | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fold1 calibration 2004 to 2013 | 3653 | 0.63 | 0.23 | +0% | 0.63 | +155% | calibration |
| fold1 VALIDATION 2014 to 2026 | 4595 | 0.59 | -0.02 | -7% | 0.66 | +295% | NO: low-flow bias |
| fold1 parameters on 1986 to 2001 (reported only) | 5807 | 0.53 | 0.05 | -31% | 0.57 | +38% | not scored |
| fold2 calibration 2014 to 2026 | 4595 | 0.54 | 0.25 | +2% | 0.61 | +168% | calibration |
| fold2 VALIDATION 2004 to 2013 | 3653 | 0.24 | -0.03 | +18% | 0.23 | +153% | NO: daily KGE, monthly KGE, low-flow bias |
| fold2 parameters on 1986 to 2001 (reported only) | 5807 | 0.61 | -0.09 | -19% | 0.71 | +25% | not scored |

**GR5J for Atibainha: fails.**

- fold1: x1 = 1441.3595, x2 = -1.2887, x3 = 14.6359, x4 = 2.3813, x5 = 0.682; rain lag 1; excluded non-positive days in validation: 0
- fold2: x1 = 1023.0787, x2 = 0.0795, x3 = 5.0, x4 = 1.1746, x5 = -0.1059; rain lag 0; excluded non-positive days in validation: 0; AT BOUND: x3

## Acceptance and parsimony

Mean validation daily KGE over both folds and both catchments: GR4J 0.562, GR5J 0.563.

- **Cachoeira:** GR4J fails, GR5J fails. **No structure accepted.**
- **Atibainha:** GR4J fails, GR5J fails. **No structure accepted.**

