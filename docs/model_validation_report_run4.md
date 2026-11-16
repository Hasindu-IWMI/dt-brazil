# Inflow model, run 4: results

Generated 2026-11-14 17:55 UTC by `pipeline/model_run4.py`. Design and test: `model_design_run4.md` (Version B), fixed and approved before the run. Run 4 recalibrates nothing: it re-scores the run 3 GR4J parameter sets for Cachoeira with the low-flow criterion on 7-day means. This is a revised, non-blind test, and the model is not claimed before 2004.

| Fold | Validation window | Daily KGE | Volume bias | Monthly KGE | 7-day blocks (lowest fifth) | Observed low flow (m3/s) | Modelled (m3/s) | Low-flow bias | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fold1 | 2014 to 2026 | 0.66 | +12% | 0.66 | 656 (131) | 0.81 | 1.49 | +84% | NO: low-flow bias |
| fold2 | 2004 to 2013 | 0.75 | -8% | 0.85 | 521 (104) | 1.55 | 2.10 | +36% | yes |

**Verdict: NOT ACCEPTED.**

## 1986 to 2001, reported and not scored

| Parameters | Daily KGE | Volume bias | Monthly KGE | 7-day low-flow bias |
| --- | --- | --- | --- | --- |
| fold1 parameters | 0.50 | +12% | 0.51 | +27% |
| fold2 parameters | 0.57 | +2% | 0.66 | +14% |

