"""Hourly station records and the radar pass table for flood run 1.

Pre-run checks 3 (first half) and 6 of docs/model_design_flood_run1.md.
Reads what fetch_flood_stations.py and fetch_s1_passes.py stored; downloads
nothing and looks at no image.

1. Hourly CSVs for the two stations, exactly as served (UTC hour, level in cm,
   discharge in m3/s where SIBH has a rating, readings in the hour):
   data/processed/flood_hourly_3E-063.csv and flood_hourly_62671200.csv.
2. For each of the 17 scored passes fixed in the design:
   - the catalogue item at that time (within 10 minutes), or none;
   - the hourly level and flow at 3E-063, and the level at 62671200, in the
     hour of the pass (the hour the pass falls in, as in the search behind
     docs/flood_option_check.md);
   - its dry references by the design's rule: same relative orbit, within 60
     days either side, 3E-063 below 240 cm in the hour of that pass. At least
     three are needed, else the pass is not scored.
   A pass is kept only if its item exists, it has three references, and the
   stage in its hour is still at least 321 cm.
   - the downstream boundary record: the 62671200 level in the 72 hours up to
     the pass. Rule added in the design's pre-run addendum and approved on
     17 November 2026, before any model or image existed: gaps of up to 3
     consecutive hours are bridged linearly (boundary input only); a pass
     with a longer gap is not scored.
3. data/processed/flood_run1_passes.json and docs/flood_run1_passes.md.

Usage: python flood_passes.py
"""
import datetime as dt
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
from fetch_s1_passes import PASSES, WINDOW_DAYS  # noqa: E402

SIBH = os.path.join(c.RAW, "sibh")
S1 = os.path.join(c.RAW, "s1")
STATIONS = {"30863": "3E-063", "14585": "62671200"}
OVERFLOW_CM, SCORE_MIN_CM, DRY_MAX_CM, MIN_REFS = 301.0, 321.0, 240.0, 3
WINDOW_H, MAX_GAP_H = 72, 3  # boundary window before each pass; longest gap that may be bridged


def hourly(sid):
    out = {}
    for path in sorted(glob.glob(os.path.join(SIBH, "flood_%s_[0-9][0-9][0-9][0-9].json.gz" % sid))):
        for r in json.load(gzip.open(path, "rt", encoding="utf-8")).get("measurements") or []:
            t = dt.datetime.strptime(str(r["date"])[:13], "%Y/%m/%d %H")
            lv, q = r.get("value"), r.get("read_value")
            out[t] = (None if lv is None else float(lv), None if q is None else float(q), r.get("qtd"))
    return out


def main():
    series = {sid: hourly(sid) for sid in STATIONS}
    for sid, code in STATIONS.items():
        rows = [(t.strftime("%Y-%m-%dT%H:00Z"), v[0], v[1], v[2]) for t, v in sorted(series[sid].items())]
        c.write_csv(os.path.join(c.PROCESSED, "flood_hourly_%s.csv" % code),
                    ["hour_utc", "level_cm", "discharge_m3s", "readings"], rows)
        print(code, "hours:", len(rows), rows[0][0] if rows else "", "to", rows[-1][0] if rows else "", flush=True)
    town, down = series["30863"], series["14585"]

    def at(s, t, k=0):
        v = s.get(t.replace(minute=0, second=0, microsecond=0))
        return None if v is None else v[k]

    out = []
    for p in PASSES:
        t = dt.datetime.fromisoformat(p)
        path = os.path.join(S1, "s1rtc_%s.json.gz" % p[:10])
        feats = json.load(gzip.open(path, "rt", encoding="utf-8"))["features"] if os.path.exists(path) else []
        items = []
        for f in feats:
            pr = f["properties"]
            items.append({"id": f["id"], "time": dt.datetime.fromisoformat(pr["datetime"][:19]),
                          "orbit": pr.get("sat:relative_orbit"), "platform": pr.get("platform"),
                          "mode": pr.get("sar:instrument_mode"), "pols": pr.get("sar:polarizations")})
        hit = min((i for i in items if abs((i["time"] - t).total_seconds()) <= 600),
                  key=lambda i: abs((i["time"] - t).total_seconds()), default=None)
        hours = [t.replace(minute=0, second=0, microsecond=0) - dt.timedelta(hours=k) for k in range(WINDOW_H, -1, -1)]
        gap = run = 0
        for h in hours:
            run = 0 if at(down, h) is not None else run + 1
            gap = max(gap, run)
        rec = {"pass": p, "stage_cm": at(town, t), "flow_m3s": at(town, t, 1), "downstream_level_cm": at(down, t),
               "downstream_hours": sum(at(down, h) is not None for h in hours), "downstream_longest_gap_h": gap,
               "item": hit["id"] if hit else None, "orbit": hit["orbit"] if hit else None,
               "platform": hit["platform"] if hit else None, "references": [], "scored": False, "why_not": ""}
        if hit:
            for i in items:
                if i is hit or i["orbit"] != hit["orbit"] or abs((i["time"] - t).days) > WINDOW_DAYS:
                    continue
                s = at(town, i["time"])
                if s is not None and s < DRY_MAX_CM:
                    rec["references"].append({"item": i["id"], "time": i["time"].strftime("%Y-%m-%dT%H:%MZ"),
                                              "stage_cm": round(s, 1)})
        if not hit:
            rec["why_not"] = "pass not in sentinel-1-rtc"
        elif rec["stage_cm"] is None or rec["stage_cm"] < SCORE_MIN_CM:
            rec["why_not"] = "stage below 321 cm or missing in the hour of the pass"
        elif len(rec["references"]) < MIN_REFS:
            rec["why_not"] = "fewer than %d dry references" % MIN_REFS
        elif gap > MAX_GAP_H:
            rec["why_not"] = "downstream level missing for %d consecutive hours" % gap
        else:
            rec["scored"] = True
        out.append(rec)

    res = {"design": "docs/model_design_flood_run1.md", "built": dt.date.today().isoformat(),
           "rules": {"overflow_cm": OVERFLOW_CM, "score_min_cm": SCORE_MIN_CM, "dry_max_cm": DRY_MAX_CM,
                     "min_references": MIN_REFS, "window_days": WINDOW_DAYS,
                     "boundary_window_h": WINDOW_H, "max_bridged_gap_h": MAX_GAP_H},
           "passes": out}
    with open(os.path.join(c.PROCESSED, "flood_run1_passes.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    lines = ["# Flood run 1: radar passes and dry references", "",
             "Generated by `pipeline/flood_passes.py` (pre-run checks 3 and 6 of",
             "`docs/model_design_flood_run1.md`). Catalogue metadata and gauge records only:",
             "no radar image has been downloaded or looked at.", "",
             "Stage, flow and downstream level are the SIBH hourly means for the hour the pass",
             "falls in. References: same relative orbit, within %d days, town gauge below %d cm." % (WINDOW_DAYS, DRY_MAX_CM),
             "Downstream hours: hours of the 62671200 level present in the %d hours up to the pass (of %d);" % (WINDOW_H, WINDOW_H + 1),
             "gaps of up to %d hours are bridged, longer ones exclude the pass." % MAX_GAP_H, "",
             "| Pass (UTC) | Orbit | Satellite | Stage 3E-063 (cm) | Flow (m³/s) | Level 62671200 (cm) | Downstream hours | Dry references | Scored |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    fmt = lambda v, d=0: "–" if v is None else ("%.*f" % (d, v))
    for r in out:
        lines.append("| %s | %s | %s | %s | %s | %s | %d | %d | %s |" % (
            r["pass"].replace("T", " "), r["orbit"] or "–", (r["platform"] or "–").replace("sentinel-", "S"),
            fmt(r["stage_cm"]), fmt(r["flow_m3s"], 1), fmt(r["downstream_level_cm"]), r["downstream_hours"],
            len(r["references"]), "yes" if r["scored"] else "no: " + r["why_not"]))
    n = sum(r["scored"] for r in out)
    lines += ["", "Scored passes: **%d of %d**." % (n, len(out)), ""]
    with open(os.path.join(c.ROOT, "docs", "flood_run1_passes.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines[9:]))


if __name__ == "__main__":
    main()
