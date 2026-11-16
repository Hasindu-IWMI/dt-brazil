"""Run 4: re-score the run 3 GR4J parameter sets for Cachoeira with the
low-flow criterion on 7-day means. Design and test: docs/model_design_run4.md,
fixed and approved before this file existed (Version B: claim narrowed to
2004 onward; 1986-2001 reported, not scored). Nothing is recalibrated here.

Usage: python model_run4.py
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
from model import CATCHMENTS, load  # noqa: E402
from model_run3 import OUT, EARLY, MIN_KGE, MAX_BIAS, MIN_MONTHLY_KGE, MAX_LOW_BIAS, build_forcing, simulate  # noqa: E402

CATCHMENT = "cachoeira_dam"
WINDOW_DAYS = 7


def low_flow_7day(days, sim, inflow, a, b):
    """Consecutive 7-day blocks from the window start with all seven days in
    the record; the fifth of blocks with the lowest observed mean; modelled
    mean over those blocks against observed mean."""
    sel = [(k, v) for k, v in zip(days, sim) if a <= k <= b]
    blocks = []
    skipped = 0
    for i in range(0, len(sel) - WINDOW_DAYS + 1, WINDOW_DAYS):
        chunk = sel[i:i + WINDOW_DAYS]
        if any(k not in inflow for k, _ in chunk):
            skipped += 1
            continue
        blocks.append((sum(inflow[k] for k, _ in chunk) / WINDOW_DAYS, sum(v for _, v in chunk) / WINDOW_DAYS))
    blocks.sort()
    low = blocks[:max(1, len(blocks) // 5)]
    obs = sum(o for o, _ in low) / len(low)
    mod = sum(m for _, m in low) / len(low)
    return {"blocks": len(blocks), "blocks_skipped": skipped, "low_blocks": len(low),
            "observed_low_m3s": obs, "modelled_low_m3s": mod, "bias_pct": (mod / obs - 1.0) * 100.0}


def main():
    cfg = CATCHMENTS[CATCHMENT]
    forcing, inflow = load(CATCHMENT)
    to_m3s = cfg["area_km2"] / 86.4
    L = ["# Inflow model, run 4: results", "",
         "Generated %s UTC by `pipeline/model_run4.py`. Design and test: `model_design_run4.md` (Version B), fixed and "
         "approved before the run. Run 4 recalibrates nothing: it re-scores the run 3 GR4J parameter sets for Cachoeira "
         "with the low-flow criterion on %d-day means. This is a revised, non-blind test, and the model is not claimed "
         "before 2004." % (dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), WINDOW_DAYS), "",
         "| Fold | Validation window | Daily KGE | Volume bias | Monthly KGE | 7-day blocks (lowest fifth) | Observed low flow (m3/s) | Modelled (m3/s) | Low-flow bias | Passed |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    accepted = True
    out = {}
    early_rows = []
    for fold in ("fold1", "fold2"):
        r = json.load(open(os.path.join(OUT, "%s_gr4j_%s.json" % (CATCHMENT, fold)), encoding="utf-8"))
        p = [r["parameters"][k] for k in ("x1", "x2", "x3", "x4")]
        days, rain, pet = build_forcing(forcing, "1984-01-01", r["last_day"], r["rain_lag_days"])
        sim = simulate("gr4j", p, rain, pet, to_m3s)
        v = r["validation"]
        lf = low_flow_7day(days, sim, inflow, r["validation_window"][0], r["validation_window"][1])
        fails = []
        if not (v["kge"] >= MIN_KGE and v["kge"] > v["benchmark_kge"]):
            fails.append("daily KGE")
        if abs(v["bias_pct"]) > MAX_BIAS:
            fails.append("volume bias")
        if v["monthly_kge"] < MIN_MONTHLY_KGE:
            fails.append("monthly KGE")
        if abs(lf["bias_pct"]) > MAX_LOW_BIAS:
            fails.append("low-flow bias")
        ok = not fails
        accepted = accepted and ok
        out[fold] = {"validation": v, "low_flow_7day": lf, "passed": ok, "fails": fails}
        L.append("| %s | %s to %s | %.2f | %+.0f%% | %.2f | %d (%d) | %.2f | %.2f | %+.0f%% | %s |" % (
            fold, r["validation_window"][0][:4], r["validation_window"][1][:4], v["kge"], v["bias_pct"], v["monthly_kge"],
            lf["blocks"], lf["low_blocks"], lf["observed_low_m3s"], lf["modelled_low_m3s"], lf["bias_pct"],
            "yes" if ok else "NO: " + ", ".join(fails)))
        e = r["early_1986_2001"]
        elf = low_flow_7day(days, sim, inflow, EARLY[0], EARLY[1])
        early_rows.append("| %s parameters | %.2f | %+.0f%% | %.2f | %+.0f%% |" % (fold, e["kge"], e["bias_pct"], e["monthly_kge"], elf["bias_pct"]))
        out[fold]["early_low_flow_7day"] = elf
    L += ["", "**Verdict: %s.**" % ("ACCEPTED under the revised test (provisional)" if accepted else "NOT ACCEPTED"), "",
          "## 1986 to 2001, reported and not scored", "",
          "| Parameters | Daily KGE | Volume bias | Monthly KGE | 7-day low-flow bias |", "| --- | --- | --- | --- | --- |"] + early_rows + [""]
    with open(os.path.join(OUT, "run4_decision.json"), "w", encoding="utf-8") as f:
        json.dump({"catchment": CATCHMENT, "accepted": accepted, "folds": out}, f, indent=1)
    with open(os.path.join(c.ROOT, "docs", "model_validation_report_run4.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
