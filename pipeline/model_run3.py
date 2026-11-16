"""Run 3 of the inflow model. The design and acceptance test are fixed in
docs/model_design_run3.md, written and approved before this file existed.
This file implements that design and must not depart from it.

  python model_run3.py job <catchment> <gr4j|gr5j> <fold1|fold2|final>
  python model_run3.py assemble

A job calibrates one model on one fold's calibration window (objective: KGE of
the square root of daily flow, days with observed inflow <= 0 excluded), then
scores it on the validation window and on 1986-2001. `assemble` applies the
acceptance and parsimony rules and writes the report.
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
from model import CATCHMENTS, load  # noqa: E402

SEED = 20261114
N_RANDOM, N_REFINE, ENSEMBLE = 3000, 1000, 30
BOUNDS = [("x1", 30.0, 5000.0, True), ("x2", -8.0, 6.0, False), ("x3", 5.0, 600.0, True),
          ("x4", 0.5, 6.0, False), ("x5", -1.0, 2.0, False)]
WET = ("2004-01-01", "2013-12-31")
DRY_START = "2014-01-01"
EARLY = ("1986-01-01", "2001-12-31")
MIN_KGE, MAX_BIAS, MIN_MONTHLY_KGE, MAX_LOW_BIAS = 0.50, 25.0, 0.60, 50.0
OUT = os.path.join(c.PROCESSED, "run3")


def kge(sim, obs):
    n = len(obs)
    if n < 30:
        return None
    ms, mo = sum(sim) / n, sum(obs) / n
    vs = sum((a - ms) ** 2 for a in sim) / n
    vo = sum((b - mo) ** 2 for b in obs) / n
    if vs <= 0 or vo <= 0 or mo == 0:
        return None
    r = sum((a - ms) * (b - mo) for a, b in zip(sim, obs)) / n / math.sqrt(vs * vo)
    return 1.0 - math.sqrt((r - 1) ** 2 + (math.sqrt(vs / vo) - 1) ** 2 + (ms / mo - 1) ** 2)


def daterange(a, b):
    d, e = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    while d <= e:
        yield d.isoformat()
        d += dt.timedelta(days=1)


def build_forcing(forcing, start, end, lag):
    """Continuous rain/PET. Rain labelled D is used on D - lag; a day with no
    gauge takes 0 mm; a day with no temperature takes the calendar-day mean PET."""
    clim = {}
    for k, r in forcing.items():
        if r["pet_mm"] not in ("", "None"):
            a = clim.setdefault(k[5:], [0.0, 0])
            a[0] += float(r["pet_mm"])
            a[1] += 1
    days, rain, pet = [], [], []
    for k in daterange(start, end):
        src = (dt.date.fromisoformat(k) + dt.timedelta(days=lag)).isoformat()
        r = forcing.get(src)
        rain.append(0.0 if r is None or r["rain_mm"] in ("", "None") else float(r["rain_mm"]))
        f = forcing.get(k)
        if f is not None and f["pet_mm"] not in ("", "None"):
            pet.append(float(f["pet_mm"]))
        else:
            a = clim.get(k[5:], [3.0, 1])
            pet.append(a[0] / a[1])
        days.append(k)
    return days, rain, pet


def simulate(model, p, rain, pet, to_m3s):
    q = gr4j.run(rain, pet, p[0], p[1], p[2], p[3], p[4] if model == "gr5j" else None)
    return [v * to_m3s for v in q]


def metrics(days, sim, inflow, a, b, bench):
    """All four acceptance quantities on the window [a, b], observed > 0 only."""
    s, o, keys = [], [], []
    dropped = 0
    for k, v in zip(days, sim):
        if a <= k <= b and k in inflow:
            if inflow[k] <= 0:
                dropped += 1
                continue
            s.append(v)
            o.append(inflow[k])
            keys.append(k)
    if len(o) < 365:
        return None
    months = {}
    for k, a_, b_ in zip(keys, s, o):
        m = months.setdefault(k[:7], [0, 0.0, 0.0])
        m[0] += 1
        m[1] += a_
        m[2] += b_
    ms = [(v[1] / v[0], v[2] / v[0]) for v in months.values() if v[0] >= 25]
    idx = sorted(range(len(o)), key=o.__getitem__)[:max(1, len(o) // 5)]
    lo_o = sum(o[i] for i in idx) / len(idx)
    lo_s = sum(s[i] for i in idx) / len(idx)
    return {"days": len(o), "nonpositive_days_excluded": dropped,
            "kge": kge(s, o), "benchmark_kge": kge([bench(k) for k in keys], o),
            "bias_pct": (sum(s) / sum(o) - 1.0) * 100.0,
            "monthly_kge": kge([x for x, _ in ms], [y for _, y in ms]) if len(ms) >= 30 else None,
            "months": len(ms), "low_flow_bias_pct": (lo_s / lo_o - 1.0) * 100.0,
            "kge_sqrt": kge([math.sqrt(x) for x in s], [math.sqrt(y) for y in o])}


def job(catchment, model, fold):
    cfg = CATCHMENTS[catchment]
    forcing, inflow = load(catchment)
    to_m3s = cfg["area_km2"] / 86.4
    last = max(k for k, r in forcing.items() if r["rain_mm"] not in ("", "None"))
    cal = {"fold1": WET, "fold2": (DRY_START, last), "final": (WET[0], last)}[fold]
    val = {"fold1": (DRY_START, last), "fold2": WET, "final": None}[fold]
    npar = 5 if model == "gr5j" else 4
    bounds = BOUNDS[:npar]
    warm = "%04d%s" % (int(cal[0][:4]) - 2, cal[0][4:])

    clim = {}
    for k, v in inflow.items():
        if cal[0] <= k <= cal[1] and v > 0:
            a = clim.setdefault(k[5:], [0.0, 0])
            a[0] += v
            a[1] += 1
    fallback = sum(a[0] for a in clim.values()) / sum(a[1] for a in clim.values())
    bench = lambda k: clim[k[5:]][0] / clim[k[5:]][1] if k[5:] in clim else fallback

    best = None
    lag_obj = {}
    for lag in (0, 1):
        rng = random.Random(SEED)
        days, rain, pet = build_forcing(forcing, warm, cal[1], lag)
        mask = [(i, math.sqrt(inflow[k])) for i, k in enumerate(days) if cal[0] <= k and k in inflow and inflow[k] > 0]
        obs = [v for _, v in mask]
        ix = [i for i, _ in mask]

        def objective(p):
            sim = simulate(model, p, rain, pet, to_m3s)
            v = kge([math.sqrt(sim[i]) for i in ix], obs)
            return -9.0 if v is None else v

        def draw():
            return [math.exp(rng.uniform(math.log(lo), math.log(hi))) if lg else rng.uniform(lo, hi) for _, lo, hi, lg in bounds]

        pool = []
        for _ in range(N_RANDOM):
            p = draw()
            pool.append((objective(p), p))
        pool.sort(reverse=True)
        bf, bp = pool[0]
        step = [0.25 if lg else 0.12 * (hi - lo) for _, lo, hi, lg in bounds]
        for it in range(N_REFINE):
            q = list(bp)
            j = rng.randrange(npar)
            _, lo, hi, lg = bounds[j]
            q[j] = q[j] * math.exp(rng.gauss(0, step[j])) if lg else q[j] + rng.gauss(0, step[j])
            q[j] = min(hi, max(lo, q[j]))
            f = objective(q)
            pool.append((f, q))
            if f > bf:
                bf, bp = f, q
            if it % 200 == 199:
                step = [s * 0.6 for s in step]
        pool.sort(reverse=True)
        lag_obj[lag] = bf
        print(catchment, model, fold, "lag", lag, "objective %.3f" % bf, [round(v, 3) for v in bp], flush=True)
        if best is None or bf > best[0]:
            best = (bf, bp, lag, pool[:ENSEMBLE])

    bf, bp, lag, ens = best
    days, rain, pet = build_forcing(forcing, "1984-01-01", last, lag)
    sim = simulate(model, bp, rain, pet, to_m3s)
    res = {"catchment": catchment, "model": model, "fold": fold, "calibration_window": cal, "validation_window": val,
           "parameters": dict(zip([b[0] for b in bounds], [round(v, 4) for v in bp])),
           "at_bound": [b[0] for b, v in zip(bounds, bp) if abs(v - b[1]) < 1e-6 * max(1, abs(b[1])) or abs(v - b[2]) < 1e-6 * abs(b[2])],
           "rain_lag_days": lag, "objective": {str(k): round(v, 4) for k, v in lag_obj.items()},
           "ensemble_objective_range": [round(ens[-1][0], 4), round(ens[0][0], 4)],
           "calibration": metrics(days, sim, inflow, cal[0], cal[1], bench),
           "validation": metrics(days, sim, inflow, val[0], val[1], bench) if val else None,
           "early_1986_2001": metrics(days, sim, inflow, EARLY[0], EARLY[1], bench), "last_day": last}
    c.ensure_dir(OUT)
    with open(os.path.join(OUT, "%s_%s_%s.json" % (catchment, model, fold)), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    if fold == "final":
        members = [simulate(model, p, rain, pet, to_m3s) for _, p in ens]
        c.write_csv(os.path.join(c.PROCESSED, "model_inflow_%s.csv" % catchment),
                    ["date", "observed_inflow_m3s", "modelled_inflow_m3s", "ensemble_low_m3s", "ensemble_high_m3s", "benchmark_m3s"],
                    [(k, inflow.get(k), round(v, 3), round(min(m[i] for m in members), 3), round(max(m[i] for m in members), 3),
                      round(bench(k), 3)) for i, (k, v) in enumerate(zip(days, sim))])


def passes(m):
    """The four criteria of docs/model_design_run3.md on one window."""
    if m is None or m["kge"] is None or m["benchmark_kge"] is None or m["monthly_kge"] is None:
        return False, ["not enough data"]
    fails = []
    if not (m["kge"] >= MIN_KGE and m["kge"] > m["benchmark_kge"]):
        fails.append("daily KGE")
    if abs(m["bias_pct"]) > MAX_BIAS:
        fails.append("volume bias")
    if m["monthly_kge"] < MIN_MONTHLY_KGE:
        fails.append("monthly KGE")
    if abs(m["low_flow_bias_pct"]) > MAX_LOW_BIAS:
        fails.append("low-flow bias")
    return not fails, fails


def assemble():
    def get(cat, model, fold):
        p = os.path.join(OUT, "%s_%s_%s.json" % (cat, model, fold))
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

    L = ["# Inflow model, run 3: results", "",
         "Generated %s UTC by `pipeline/model_run3.py`. Design and acceptance test: `model_design_run3.md`, fixed and "
         "approved before the run. This was not a blind test: every period had been examined in runs 1 and 2." %
         dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "",
         "Criteria in each validation window: daily KGE >= %.2f and above the benchmark; volume bias within %.0f%%; "
         "monthly KGE >= %.2f; low-flow bias within %.0f%%." % (MIN_KGE, MAX_BIAS, MIN_MONTHLY_KGE, MAX_LOW_BIAS), ""]
    verdict = {}
    val_kges = {"gr4j": [], "gr5j": []}
    row = lambda label, m, ok, fails: "| %s | %d | %.2f | %.2f | %+.0f%% | %s | %+.0f%% | %s |" % (
        label, m["days"], m["kge"], m["benchmark_kge"], m["bias_pct"],
        "n/a" if m["monthly_kge"] is None else "%.2f" % m["monthly_kge"], m["low_flow_bias_pct"],
        "calibration" if ok is None else ("yes" if ok else "NO: " + ", ".join(fails)))
    for cat, cfg in CATCHMENTS.items():
        L += ["## %s (%.0f km2)" % (cfg["label"], cfg["area_km2"]), ""]
        for model in ("gr4j", "gr5j"):
            ok_all = True
            L += ["### %s" % model.upper(), "",
                  "| Window | Days | Daily KGE | Benchmark | Volume bias | Monthly KGE | Low-flow bias | Passed |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"]
            notes = []
            for fold in ("fold1", "fold2"):
                r = get(cat, model, fold)
                if r is None:
                    L.append("| %s | job missing | | | | | | |" % fold)
                    ok_all = False
                    continue
                L.append(row("%s calibration %s to %s" % (fold, r["calibration_window"][0][:4], r["calibration_window"][1][:4]),
                             r["calibration"], None, None))
                ok, fails = passes(r["validation"])
                L.append(row("%s VALIDATION %s to %s" % (fold, r["validation_window"][0][:4], r["validation_window"][1][:4]),
                             r["validation"], ok, fails))
                ok_all = ok_all and ok
                if r["validation"]["kge"] is not None:
                    val_kges[model].append(r["validation"]["kge"])
                e = r["early_1986_2001"]
                if e is not None:
                    eok, efails = passes(e)
                    if cat == "cachoeira_dam":
                        L.append(row("%s parameters on 1986 to 2001 (scored)" % fold, e, eok, efails))
                        ok_all = ok_all and eok
                    else:
                        L.append(row("%s parameters on 1986 to 2001 (reported only)" % fold, e, None, None).replace("calibration", "not scored"))
                notes.append("%s: %s; rain lag %d; excluded non-positive days in validation: %d%s" % (
                    fold, ", ".join("%s = %s" % kv for kv in r["parameters"].items()), r["rain_lag_days"],
                    r["validation"]["nonpositive_days_excluded"],
                    "; AT BOUND: " + ", ".join(r["at_bound"]) if r["at_bound"] else ""))
            verdict[(cat, model)] = ok_all
            L += ["", "**%s for %s: %s.**" % (model.upper(), cfg["label"], "passes every scored window" if ok_all else "fails"), ""]
            L += ["- " + n for n in notes] + [""]

    mean = {m: (sum(v) / len(v) if v else None) for m, v in val_kges.items()}
    L += ["## Acceptance and parsimony", "",
          "Mean validation daily KGE over both folds and both catchments: GR4J %s, GR5J %s." %
          tuple("n/a" if mean[m] is None else "%.3f" % mean[m] for m in ("gr4j", "gr5j")), ""]
    chosen = {}
    for cat, cfg in CATCHMENTS.items():
        g4, g5 = verdict[(cat, "gr4j")], verdict[(cat, "gr5j")]
        if g4 and not g5:
            pick = "gr4j"
        elif g5 and not g4:
            pick = "gr5j"  # passes a test GR4J fails
        elif g4 and g5:
            pick = "gr5j" if (mean["gr5j"] or 0) - (mean["gr4j"] or 0) >= 0.05 else "gr4j"
        else:
            pick = None
        chosen[cat] = pick
        L.append("- **%s:** GR4J %s, GR5J %s. %s" % (cfg["label"], "passes" if g4 else "fails", "passes" if g5 else "fails",
                                                    "Accepted structure: %s." % pick.upper() if pick else "**No structure accepted.**"))
    L.append("")
    with open(os.path.join(OUT, "decision.json"), "w", encoding="utf-8") as f:
        json.dump({"chosen": chosen, "mean_validation_kge": mean}, f, indent=1)
    with open(os.path.join(c.ROOT, "docs", "model_validation_report_run3.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    if sys.argv[1] == "job":
        job(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        assemble()
