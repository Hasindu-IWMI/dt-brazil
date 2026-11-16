"""Calibrate GR4J on reservoir inflow and test it on independent periods.

THE TEST WAS FIXED BEFORE ANY RUN (do not edit after seeing results):

  Target        daily natural inflow to the reservoir, as reported in ANA SAR
  Calibration   2004-01-01 to 2013-12-31 (warm-up from 2002-01-01), objective KGE
  Validation A  2014-01-01 to 2016-12-31  drought and recovery (a different
                regime from calibration: differential split-sample, Klemes 1986)
  Validation B  2017-01-01 to the end of the record
  Validation C  1986-01-01 to 2001-12-31  earlier decades
  Benchmark     mean inflow for each calendar day, computed from the
                calibration period only (a model that knows the seasons)
  Acceptance    in EVERY validation period: KGE above the benchmark's KGE,
                KGE >= 0.50, and |volume bias| <= 25 %
  Parameters    frozen after calibration; nothing is re-tuned on validation data

Rain-day convention: ANA daily rain is read in the morning, so the rain
labelled day D may belong mostly to D-1. Both alignments are tried ON THE
CALIBRATION PERIOD ONLY and the better one is kept.

Uncertainty: the ENSEMBLE best parameter sets from the search are kept and
their spread is reported; it reflects parameter uncertainty only, not errors
in rain, evapotranspiration or the inflow record itself.

RUN HISTORY
  Run 1 (14 Nov 2026)  rainfall as downloaded. Both catchments NOT ACCEPTED.
                       Archived as docs/model_validation_report_run1_unaudited.md.
  Run 2 (14 Nov 2026)  the ONLY change is the rainfall input: gauge-months and
                       gauge-years flagged by audit_rain.py (which uses no model
                       output) are treated as missing. Model, parameter bounds,
                       search, random seed, periods and acceptance criteria are
                       identical to run 1 and were restated here before run 2
                       started. Caveat: the validation periods were seen once,
                       in run 1, so run 2 is not a blind test. Expectation
                       written before the run: Atibainha should improve after
                       2017; Cachoeira's rainfall barely changed, so its drought
                       bias should remain.

Usage: python model.py [catchment ...]
"""
import datetime as dt
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
import gr4j  # noqa: E402

WARMUP_START = "2002-01-01"
CAL = ("2004-01-01", "2013-12-31")
VAL = {"A_drought_2014_2016": ("2014-01-01", "2016-12-31"),
       "B_recent_2017_on": ("2017-01-01", "2099-12-31"),
       "C_early_1986_2001": ("1986-01-01", "2001-12-31")}
MIN_KGE = 0.50
MAX_ABS_BIAS_PCT = 25.0
BOUNDS = {"x1": (30.0, 2500.0), "x2": (-8.0, 6.0), "x3": (5.0, 600.0), "x4": (0.5, 6.0)}
N_RANDOM = 1500
N_REFINE = 500
ENSEMBLE = 30
SEED = 20261114

CATCHMENTS = {
    "cachoeira_dam": {"reservoir": "cachoeira", "area_km2": 392.0, "label": "Cachoeira"},
    "atibainha_dam": {"reservoir": "atibainha", "area_km2": 312.0, "label": "Atibainha"},
}


def kge_parts(sim, obs):
    n = len(obs)
    if n < 30:
        return None
    ms = sum(sim) / n
    mo = sum(obs) / n
    vs = sum((a - ms) ** 2 for a in sim) / n
    vo = sum((b - mo) ** 2 for b in obs) / n
    if vs <= 0 or vo <= 0 or mo == 0:
        return None
    r = sum((a - ms) * (b - mo) for a, b in zip(sim, obs)) / n / math.sqrt(vs * vo)
    alpha = math.sqrt(vs / vo)
    beta = ms / mo
    kge = 1.0 - math.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)
    nse = 1.0 - sum((a - b) ** 2 for a, b in zip(sim, obs)) / (vo * n)
    return {"kge": kge, "r": r, "alpha": alpha, "beta": beta, "nse": nse, "bias_pct": (beta - 1.0) * 100.0, "n": n}


def low_flow_error(sim, obs):
    """Relative error of the mean of the lowest 10 % of observed days."""
    idx = sorted(range(len(obs)), key=obs.__getitem__)[:max(1, len(obs) // 10)]
    o = sum(obs[i] for i in idx) / len(idx)
    s = sum(sim[i] for i in idx) / len(idx)
    return (s - o) / o * 100.0 if o > 0 else None


def load(catchment):
    cfg = CATCHMENTS[catchment]
    forcing = {r["date"]: r for r in c.read_csv(os.path.join(c.PROCESSED, "forcing_%s.csv" % catchment))}
    inflow = {r["date"]: float(r["inflow_m3s"]) for r in
              c.read_csv(os.path.join(c.PROCESSED, "sar_%s.csv" % cfg["reservoir"])) if r["inflow_m3s"] not in ("", "None")}
    return forcing, inflow


def series(forcing, start, end, lag):
    """Continuous daily rain/PET from start to end. Rain labelled D is used on
    D - lag. A day with no rain gauge takes 0 mm and is counted; a day with no
    temperature takes the calendar-day mean PET."""
    days = []
    d = dt.date.fromisoformat(start)
    e = dt.date.fromisoformat(end)
    while d <= e:
        days.append(d.isoformat())
        d += dt.timedelta(days=1)
    pet_clim = {}
    for k, r in forcing.items():
        if r["pet_mm"] not in ("", "None"):
            a = pet_clim.setdefault(k[5:], [0.0, 0])
            a[0] += float(r["pet_mm"])
            a[1] += 1
    rain, pet = [], []
    no_rain = 0
    for k in days:
        src = (dt.date.fromisoformat(k) + dt.timedelta(days=lag)).isoformat()
        r = forcing.get(src)
        if r is None or r["rain_mm"] in ("", "None"):
            rain.append(0.0)
            no_rain += 1
        else:
            rain.append(float(r["rain_mm"]))
        f = forcing.get(k)
        if f is not None and f["pet_mm"] not in ("", "None"):
            pet.append(float(f["pet_mm"]))
        else:
            a = pet_clim.get(k[5:], [3.0, 1])
            pet.append(a[0] / a[1])
    return days, rain, pet, no_rain


def score(days, sim_m3s, inflow, a, b):
    s, o = [], []
    for k, v in zip(days, sim_m3s):
        if a <= k <= b and k in inflow:
            s.append(v)
            o.append(inflow[k])
    return s, o


def main():
    names = sys.argv[1:] or list(CATCHMENTS)
    results = {}
    report = ["# Inflow model: calibration and validation", "",
              "Generated %s UTC by `pipeline/model.py`. The test design is fixed in that file's header and was "
              "written before the first run." % dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "",
              "**This is run 2.** The only change from run 1 is the rainfall input, now audited by "
              "`pipeline/audit_rain.py`. The test is unchanged. The validation periods were seen once in run 1, "
              "so this is not a blind test. Run 1 is archived as `model_validation_report_run1_unaudited.md`.", "",
              "Model: GR4J, daily, four parameters. Target: natural inflow reported by ANA SAR. "
              "Acceptance in every validation period: KGE above the calendar-day benchmark, KGE >= %.2f, "
              "volume bias within %.0f%%." % (MIN_KGE, MAX_ABS_BIAS_PCT), ""]
    last_day = dt.date.today().isoformat()
    for name in names:
        cfg = CATCHMENTS[name]
        forcing, inflow = load(name)
        to_m3s = cfg["area_km2"] / 86.4
        rng = random.Random(SEED)

        # benchmark: calendar-day mean inflow from the calibration period only
        clim = {}
        for k, v in inflow.items():
            if CAL[0] <= k <= CAL[1]:
                a = clim.setdefault(k[5:], [0.0, 0])
                a[0] += v
                a[1] += 1
        bench = lambda k: (clim[k[5:]][0] / clim[k[5:]][1]) if k[5:] in clim else clim["02-28"][0] / clim["02-28"][1]

        best_overall = None
        lag_scores = {}
        for lag in (0, 1):
            days, rain, pet, _ = series(forcing, WARMUP_START, CAL[1], lag)

            def objective(p):
                sim = gr4j.run(rain, pet, p[0], p[1], p[2], p[3])
                s, o = score(days, [q * to_m3s for q in sim], inflow, CAL[0], CAL[1])
                parts = kge_parts(s, o)
                return -9.0 if parts is None else parts["kge"]

            pool = []
            lo = [BOUNDS[k][0] for k in ("x1", "x2", "x3", "x4")]
            hi = [BOUNDS[k][1] for k in ("x1", "x2", "x3", "x4")]
            for _ in range(N_RANDOM):
                p = [math.exp(rng.uniform(math.log(lo[0]), math.log(hi[0]))), rng.uniform(lo[1], hi[1]),
                     math.exp(rng.uniform(math.log(lo[2]), math.log(hi[2]))), rng.uniform(lo[3], hi[3])]
                pool.append((objective(p), p))
            pool.sort(reverse=True)
            best_f, best_p = pool[0]
            step = [0.25, 0.8, 0.25, 0.5]  # relative for x1, x3; absolute for x2, x4
            for it in range(N_REFINE):
                q = list(best_p)
                j = rng.randrange(4)
                if j in (0, 2):
                    q[j] *= math.exp(rng.gauss(0, step[j]))
                else:
                    q[j] += rng.gauss(0, step[j])
                q[j] = min(hi[j], max(lo[j], q[j]))
                f = objective(q)
                pool.append((f, q))
                if f > best_f:
                    best_f, best_p = f, q
                if it % 100 == 99:
                    step = [s * 0.6 for s in step]
            pool.sort(reverse=True)
            lag_scores[lag] = best_f
            print(name, "lag", lag, "calibration KGE %.3f" % best_f, [round(v, 3) for v in best_p], flush=True)
            if best_overall is None or best_f > best_overall[0]:
                best_overall = (best_f, best_p, lag, pool[:ENSEMBLE])

        best_f, best_p, lag, ensemble = best_overall
        # stop at the last day any rain gauge reports: beyond it there is no forcing
        last_day = max(k for k, r in forcing.items() if r["rain_mm"] not in ("", "None"))
        days, rain, pet, no_rain = series(forcing, "1984-01-01", last_day, lag)
        sim = [q * to_m3s for q in gr4j.run(rain, pet, *best_p)]
        members = [[q * to_m3s for q in gr4j.run(rain, pet, *p)] for _, p in ensemble]
        lo_band = [min(m[i] for m in members) for i in range(len(days))]
        hi_band = [max(m[i] for m in members) for i in range(len(days))]

        periods = dict(VAL)
        periods = {"calibration_2004_2013": CAL, **periods}
        rows = {}
        accepted = True
        for pname, (a, b) in periods.items():
            s, o = score(days, sim, inflow, a, b)
            parts = kge_parts(s, o)
            keys = [k for k in days if a <= k <= b and k in inflow]
            bparts = kge_parts([bench(k) for k in keys], [inflow[k] for k in keys])
            inside = sum(1 for k, l, h in zip(days, lo_band, hi_band) if a <= k <= b and k in inflow and l <= inflow[k] <= h)
            row = {"model": parts, "benchmark": bparts, "low_flow_error_pct": low_flow_error(s, o) if parts else None,
                   "obs_inside_ensemble_pct": inside / len(keys) * 100.0 if keys else None,
                   "first": keys[0] if keys else None, "last": keys[-1] if keys else None}
            if pname != "calibration_2004_2013":
                ok = (parts is not None and bparts is not None and parts["kge"] > bparts["kge"]
                      and parts["kge"] >= MIN_KGE and abs(parts["bias_pct"]) <= MAX_ABS_BIAS_PCT)
                row["passed"] = ok
                accepted = accepted and ok
            rows[pname] = row

        results[name] = {
            "label": cfg["label"], "area_km2": cfg["area_km2"], "accepted": accepted,
            "parameters": dict(zip(("x1", "x2", "x3", "x4"), [round(v, 4) for v in best_p])),
            "rain_lag_days": lag, "lag_calibration_kge": {str(k): round(v, 4) for k, v in lag_scores.items()},
            "ensemble_size": len(ensemble),
            "ensemble_kge_range": [round(ensemble[-1][0], 4), round(ensemble[0][0], 4)],
            "ensemble_parameter_range": {k: [round(min(p[i] for _, p in ensemble), 3), round(max(p[i] for _, p in ensemble), 3)]
                                         for i, k in enumerate(("x1", "x2", "x3", "x4"))},
            "days_without_rain_gauge": no_rain, "periods": rows,
        }
        c.write_csv(os.path.join(c.PROCESSED, "model_inflow_%s.csv" % name),
                    ["date", "observed_inflow_m3s", "modelled_inflow_m3s", "ensemble_low_m3s", "ensemble_high_m3s", "benchmark_m3s"],
                    [(k, inflow.get(k), round(v, 3), round(l, 3), round(h, 3), round(bench(k), 3))
                     for k, v, l, h in zip(days, sim, lo_band, hi_band)])

        report += ["## %s (%.0f km2)" % (cfg["label"], cfg["area_km2"]), "",
                   "**Verdict: %s.**" % ("ACCEPTED: passed every validation period" if accepted else
                                         "NOT ACCEPTED: failed at least one validation period"), "",
                   "- Parameters: x1 = %.1f mm, x2 = %.2f mm/day, x3 = %.1f mm, x4 = %.2f days." % tuple(best_p),
                   "- Rain alignment chosen on the calibration period: rain labelled D used on D%s (calibration KGE %.3f; the other alignment gave %.3f)." %
                   ("" if lag == 0 else " - 1", lag_scores[lag], lag_scores[1 - lag]),
                   "- Parameter ensemble: best %d sets, calibration KGE %.3f to %.3f." %
                   (len(ensemble), ensemble[-1][0], ensemble[0][0]),
                   "- Days from 1984 with no rain gauge reporting (rain taken as 0): %d." % no_rain, "",
                   "| Period | Days | KGE | Benchmark KGE | Correlation | Variability ratio | Volume bias | NSE | Low-flow error | Observed inside ensemble | Passed |",
                   "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for pname, row in rows.items():
            m, b = row["model"], row["benchmark"]
            if m is None:
                report.append("| %s | too few days | | | | | | | | | |" % pname)
                continue
            report.append("| %s | %d | %.2f | %.2f | %.2f | %.2f | %+.0f%% | %.2f | %s | %.0f%% | %s |" % (
                pname, m["n"], m["kge"], b["kge"] if b else float("nan"), m["r"], m["alpha"], m["bias_pct"], m["nse"],
                "n/a" if row["low_flow_error_pct"] is None else "%+.0f%%" % row["low_flow_error_pct"],
                row["obs_inside_ensemble_pct"], "calibration" if "passed" not in row else ("yes" if row["passed"] else "NO")))
        report.append("")

    report += ["## How to read this", "",
               "- KGE is 1 for a perfect match. The benchmark column is a model that only knows the average seasonal cycle; "
               "a rainfall-runoff model is worth having only where it beats that.",
               "- Variability ratio below 1 means the model is too smooth; volume bias is total modelled over observed volume.",
               "- Low-flow error is the error in the mean of the driest tenth of observed days.",
               "- The ensemble spread covers parameter uncertainty only. A low share of observations inside it means "
               "the errors come from elsewhere: rainfall sampling, evaporation, the inflow record, or the model structure.",
               "- The inflow record is itself computed by the operator from a reservoir balance and contains negative days.", ""]
    with open(os.path.join(c.ROOT, "docs", "model_validation_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    with open(os.path.join(c.PROCESSED, "model_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    print("report: docs/model_validation_report.md")


if __name__ == "__main__":
    main()
