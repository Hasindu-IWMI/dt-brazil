# Inflow model, run 4: design and test, fixed before any run

Written 14 November 2026. Nothing in this file may be changed after run 4
starts. Run 4 has not been run, and its low-flow score has not been computed
or looked at in any form.

## What run 4 is, stated plainly

Run 4 **changes a criterion after a model failed it**. That is normally bad
practice. It is proposed only because a data-only test, using no model
output, shows the run 3 low-flow criterion was biased by construction. Even
so, a pass in run 4 would be weaker evidence than a pass in run 3 would have
been, and the result must be labelled that way.

Run 4 also **does not recalibrate anything**. It re-scores the run 3 GR4J
parameter sets for Cachoeira.

## The evidence for changing the low-flow criterion (no model involved)

In rainless spells (no rain for six days) true inflow should recede smoothly.
In the operator's daily inflow record for Cachoeira it does not:

| Period | Rainless days | Median inflow (m³/s) | Days on which inflow rises with no rain | Lag-1 autocorrelation of daily changes | Implied noise per day (m³/s) |
| --- | --- | --- | --- | --- | --- |
| 1986–2001 | 992 | 3.38 | 50% | −0.37 | about 1.0 |
| 2004–2013 | 804 | 2.13 | 48% | −0.43 | about 1.0 |
| 2014–2026 | 1,037 | 1.47 | 46% | −0.32 | about 0.55 |

Inflow rising on half of all rainless days, with successive changes strongly
anti-correlated, is the signature of independent day-to-day error (pure white
noise gives −0.5). Its size is about half of the dry-weather inflow itself.

Run 3's criterion took the lowest fifth of single days. With noise this
large, that selects the days on which the error happened to be negative, so
the "observed" low flow is biased low and any correct model appears to
overestimate. The criterion was mine and it was badly designed.

A correction to an earlier statement: after run 3 the report said the
record's median day-to-day change (1.12 m³/s) showed it was "as noisy as its
own low flows". That measure mixed real variability with noise and did not
shrink with averaging, so it proved nothing. The rainless-spell test above is
the valid evidence.

## Choice of averaging window, by a rule fixed before computing

Rule: the shortest of 3, 7, 14 or 30 days for which the noise of the window
mean (daily noise ÷ √days) is at most 20% of the median rainless inflow in
every period. The 20% is a judgement.

| Window | 1986–2001 | 2004–2013 | 2014–2026 | Meets rule |
| --- | --- | --- | --- | --- |
| 3 days | 17% | 28% | 22% | No |
| 7 days | 11% | 18% | 14% | **Yes** |
| 14 days | 8% | 13% | 10% | Yes |

The window is **7 days**.

## A second problem that run 4 cannot avoid

In run 3, Cachoeira's fold 1 parameters also failed on the 1986–2001 record
for reasons unrelated to low flow: daily KGE just under 0.50 and monthly KGE
0.51 against 0.60. Changing the low-flow criterion does not touch that.

So there are only two honest versions of run 4:

- **Version A, full claim.** Keep the 1986–2001 check as pass/fail. The
  outcome is already known: not accepted. There is no point running it.
- **Version B, narrowed claim.** The model is claimed valid only for
  conditions from 2004 onward, which is what present-day operation needs. The
  1986–2001 result is reported in full but not scored. This is a second
  post-hoc change, and there is no independent evidence that the early
  Cachoeira record is faulty; it is a narrowing of what is claimed, not a
  correction.

**This design is Version B.** If that narrowing is not acceptable, run 4
should not be run and the pilot stays an observed-record tool.

## Scope

- Catchment: Cachoeira only. Atibainha failed run 3 on skill and volume, and
  is not revisited.
- Model: GR4J only. Run 3's parsimony rule settled that GR5J adds nothing.
- Parameters: the two run 3 sets (fold 1 and fold 2), unchanged.

## Acceptance, fixed here

In the validation window of **both** folds:

1. Daily KGE at least 0.50 and above the calendar-day benchmark (unchanged;
   already met in run 3).
2. Volume bias within ±25% (unchanged; already met).
3. Monthly-mean KGE at least 0.60 (unchanged; already met).
4. **Low-flow bias within ±50%, on 7-day means**: split the window into
   consecutive 7-day blocks with all seven days present, take the fifth of
   blocks with the lowest observed mean, and compare the modelled mean over
   those blocks with the observed mean. The tolerance is unchanged.

Because 1 to 3 are already known to be met, criterion 4 alone decides run 4.

## If it passes

1. One final calibration on 2004 to the end of the record.
2. Modelled Cachoeira inflow may appear in the viewer, labelled
   **"provisional: passed a revised, non-blind test; not claimed before 2004;
   awaiting forward test"**.
3. Proxy-basin check: the same parameters run, untuned, on the independent
   351 km² area between the dams and the Atibaia gauge. Reported.
4. Forward test: the model is frozen and compared with inflow records as they
   arrive. **This is the decisive test.** A pre-stated failure rule applies:
   if, over the first twelve months of new records, monthly KGE falls below
   0.60 or volume bias exceeds ±25%, the provisional label is replaced by
   "failed forward test" and the modelled series is withdrawn.

## If it fails

No run 5 on this record. The pilot stays an observed-record tool until
different data arrive (state-network or CEMADEN rainfall, or the operator's
measured flows).

## Expectation, written before the run

The low-flow bias should fall well below the +104% and +158% of run 3,
because the selection bias is largely removed. Whether it falls under 50% is
genuinely uncertain: the models overestimated low flows in calibration too,
and part of that may be a real fault (recessions that are too slow), not
noise.

## What this design does not fix

- The daily-KGE criterion is also depressed by the same noise; it is left
  unchanged, which is conservative.
- Evaporation demand still comes from reanalysis temperature.
- Rain coverage is thin after 2022.
- Uncertainty is still reported from parameter spread only.
