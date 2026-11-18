"""Pre-run check 1 of flood run 2 (docs/model_design_flood_run2.md): the evening Stripmap passes.

Catalogue search, metadata only, in Microsoft Planetary Computer's `sentinel-1-grd` collection
(Copernicus Sentinel data, free and open) for Stripmap (SM) scenes over Atibaia town on ascending
passes (about 21:35-21:44 UTC), October 2014 to November 2026, one query per year. Raw responses are
stored gzip-compressed in data/raw/s1/ and logged in the manifest. No image is downloaded or read:
the design keeps the evening scenes unseen until the mapping rule is applied to all of them at once.

Then the design's rules, applied to the hourly records (data/processed/flood_hourly_*.csv):
- a candidate is a pass with 3E-063 at 321 cm or more in the hour of the pass, from 2 days before
  to 6 days after a flood peak. Which floods' peaks is set by --peaks (see the addendum):
    option-check  the peak days of docs/flood_option_check.md section 2 (daily mean stage; peaks
                  less than 10 days apart count once), the list the design's expected table used
    project       the floods of data/processed/flood_gauges.json (daily maximum; floods less than
                  10 days apart joined), peak day in local time (UTC-3)
    none          no peak window: every pass at 321 cm or more
  All three are computed and reported; the scored list follows --peaks (default option-check);
- event start (change 1): the last hour before the pass at which 3E-063 stood below the overflow
  level (301 cm), searched back up to 14 days;
- gaps (run 1's rule, over the whole event window, from the event start to the pass): a gap of up to
  3 consecutive hours in the 62671200 level or in the 3E-063 flow is bridged; a longer one excludes
  the pass;
- dry references: Stripmap scenes of the same relative orbit and polarisation within 60 days either
  side, with 3E-063 below 240 cm in the hour of the scene; the 8 nearest in time; at least 3.

Writes data/processed/flood_run2_passes.json and docs/flood_run2_passes.md. Standard library only.
Not part of run_all.py: it serves one fixed experiment. Usage: python pipeline/fetch_s1_sm_passes.py
"""
import csv
import datetime as dt
import re
import gzip
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

API = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SOURCE = "Microsoft Planetary Computer STAC API, collection sentinel-1-grd (Stripmap, ascending)"
RAW_DIR = os.path.join(c.RAW, "s1")
BBOX = [-46.62, -23.16, -46.50, -23.06]  # Atibaia town reach, as run 1 and the option check searched
YEARS = range(2014, 2027)
OVERFLOW_CM, SCORE_MIN_CM, DRY_MAX_CM = 301.0, 321.0, 240.0
BEFORE_D, AFTER_D = 2, 6  # pass window around each flood peak (days)
START_SEARCH_H = 14 * 24  # change 1: look back this far for the last in-bank hour
MAX_GAP_H = 3
REF_DAYS, REF_CAP, MIN_REFS = 60, 8, 3
LOCAL = dt.timedelta(hours=-3)


def post(body, tries=5):
    data = json.dumps(body).encode("utf-8")
    for k in range(tries):
        try:
            req = urllib.request.Request(API, data=data, headers={"Content-Type": "application/json", "User-Agent": "upper-atibaia-pipeline/0.1"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if k == tries - 1:
                raise
            print("  retry", k + 1, type(e).__name__, e, flush=True)
            time.sleep(15 * (k + 1))


def fetch():
    """One catalogue query per year, stored raw. Resumable: years already on disk are skipped."""
    for y in YEARS:
        path = os.path.join(RAW_DIR, "s1grd_sm_asc_%d.json.gz" % y)
        if os.path.exists(path):
            continue
        a = "2014-10-01T00:00:00Z" if y == 2014 else "%d-01-01T00:00:00Z" % y
        b = "2026-11-17T23:59:59Z" if y == 2026 else "%d-12-31T23:59:59Z" % y
        body = {"collections": ["sentinel-1-grd"], "bbox": BBOX, "datetime": "%s/%s" % (a, b), "limit": 500,
                "query": {"sar:instrument_mode": {"eq": "SM"}, "sat:orbit_state": {"eq": "ascending"}}}
        data = post(body)
        d = json.loads(data.decode("utf-8"))
        n = len(d.get("features") or [])
        if any(l.get("rel") == "next" for l in d.get("links") or []):
            raise RuntimeError("more than one page for %d: raise the limit" % y)
        c.write_bytes(path, gzip.compress(data, 9, mtime=0))
        c.append_manifest({"source": SOURCE, "url": API, "query": body, "file": os.path.relpath(path, c.ROOT).replace("\\", "/"),
                           "bytes": len(data), "sha256": c.sha256(data), "stored": "gzip", "items": n})
        print("year", y, "items:", n, flush=True)
        time.sleep(1.0)


def hourly(code):
    out = {}
    with open(os.path.join(c.PROCESSED, "flood_hourly_%s.csv" % code), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = dt.datetime.strptime(r["hour_utc"], "%Y-%m-%dT%H:00Z")
            lv = float(r["level_cm"]) if r["level_cm"] not in ("", "None") else None
            q = float(r["discharge_m3s"]) if r["discharge_m3s"] not in ("", "None") else None
            out[t] = (lv, q)
    return out


def longest_gap(series, k, t0, t1):
    """Longest run of hours without a value (index k) from t0 to t1 inclusive."""
    gap = run = 0
    h = t0
    while h <= t1:
        v = series.get(h)
        run = 0 if v is not None and v[k] is not None else run + 1
        gap = max(gap, run)
        h += dt.timedelta(hours=1)
    return gap


def option_check_peaks():
    """Peak days of the flood table in docs/flood_option_check.md section 2."""
    text = open(os.path.join(c.ROOT, "docs", "flood_option_check.md"), encoding="utf-8").read()
    sec = text.split("## 2.", 1)[1].split("\n## ", 1)[0]
    return sorted({dt.date.fromisoformat(m) for m in re.findall(r"^\| (\d{4}-\d{2}-\d{2}) \|", sec, flags=re.M)})


def main():
    mode = sys.argv[sys.argv.index("--peaks") + 1] if "--peaks" in sys.argv else "option-check"
    assert mode in ("option-check", "project", "none"), mode
    os.makedirs(RAW_DIR, exist_ok=True)
    fetch()
    items = {}
    for y in YEARS:
        for f in json.load(gzip.open(os.path.join(RAW_DIR, "s1grd_sm_asc_%d.json.gz" % y), "rt", encoding="utf-8"))["features"]:
            p = f["properties"]
            items[f["id"]] = {"id": f["id"], "time": dt.datetime.fromisoformat(p["datetime"][:19]), "orbit": p.get("sat:relative_orbit"),
                              "pols": p.get("sar:polarizations"), "platform": p.get("platform"), "beam": f["id"].split("_")[1],
                              "orbit_source": p.get("s1:orbit_source"), "start": p.get("start_datetime", p["datetime"])[:19]}
    # one entry per acquisition: the catalogue lists some twice (processed twice, same start time). Keep
    # the one geolocated with the precise orbit (POEORB) if there is one, else the last by id. (No pass
    # over the town comes as two adjacent slices; checked when this was written.)
    by_pass = {}
    for i in sorted(items.values(), key=lambda i: (i["orbit_source"] == "POEORB", i["id"])):
        by_pass[(i["orbit"], i["start"])] = i
    scenes = sorted(by_pass.values(), key=lambda i: i["time"])
    duplicates = len(items) - len(scenes)
    town, down = hourly("3E-063"), hourly("62671200")
    hour = lambda t: t.replace(minute=0, second=0, microsecond=0)
    stage = lambda t: (town.get(hour(t)) or (None, None))[0]
    with open(os.path.join(c.PROCESSED, "flood_gauges.json"), encoding="utf-8") as f:
        peaks = {"project": [dt.date.fromisoformat(e["peak_date"]) for e in json.load(f)["events"]],
                 "option-check": option_check_peaks()}
    near = lambda day, key: [p for p in peaks[key] if p - dt.timedelta(days=BEFORE_D) <= day <= p + dt.timedelta(days=AFTER_D)]

    out = []
    for s in scenes:
        local_day = (s["time"] + LOCAL).date()
        st = stage(s["time"])
        if st is None or st < SCORE_MIN_CM:
            continue
        win = {k: near(local_day, k) for k in peaks}
        win["none"] = [None]
        t1 = hour(s["time"])
        start = None
        for k in range(1, START_SEARCH_H + 1):
            v = town.get(t1 - dt.timedelta(hours=k))
            if v is not None and v[0] is not None and v[0] < OVERFLOW_CM:
                start = t1 - dt.timedelta(hours=k)
                break
        rec = {"pass": s["time"].strftime("%Y-%m-%dT%H:%MZ"), "item": s["id"], "orbit": s["orbit"], "beam": s["beam"],
               "pols": s["pols"], "platform": s["platform"], "orbit_source": s["orbit_source"],
               "peak_option_check": str(win["option-check"][0]) if win["option-check"] else None,
               "peak_project": str(win["project"][0]) if win["project"] else None,
               "stage_cm": round(st, 1), "flow_m3s": None if town[t1][1] is None else round(town[t1][1], 1),
               "event_start": start.strftime("%Y-%m-%dT%H:00Z") if start else None,
               "event_days": round((t1 - start).total_seconds() / 86400, 1) if start else None,
               "gap_62671200_h": None, "gap_3E063_flow_h": None, "references": [], "scored": False, "why_not": ""}
        if start:
            rec["gap_62671200_h"] = longest_gap(down, 0, start, t1)
            rec["gap_3E063_flow_h"] = longest_gap(town, 1, start, t1)
        refs = []
        for r in scenes:
            if r is s or r["orbit"] != s["orbit"] or r["pols"] != s["pols"] or abs((r["time"] - s["time"]).days) > REF_DAYS:
                continue
            rs = stage(r["time"])
            if rs is not None and rs < DRY_MAX_CM:
                refs.append((abs((r["time"] - s["time"]).total_seconds()), r, rs))
        rec["references"] = [{"item": r["id"], "time": r["time"].strftime("%Y-%m-%dT%H:%MZ"), "stage_cm": round(rs, 1)}
                             for _, r, rs in sorted(refs, key=lambda x: x[0])[:REF_CAP]]
        rules_ok = {}
        if not start:
            rec["why_not"] = "no hour below 301 cm in the 14 days before"
        elif rec["gap_62671200_h"] > MAX_GAP_H:
            rec["why_not"] = "62671200 level missing for %d consecutive hours" % rec["gap_62671200_h"]
        elif rec["gap_3E063_flow_h"] > MAX_GAP_H:
            rec["why_not"] = "3E-063 flow missing for %d consecutive hours" % rec["gap_3E063_flow_h"]
        elif len(rec["references"]) < MIN_REFS:
            rec["why_not"] = "fewer than %d dry references" % MIN_REFS
        else:
            rec["scored"] = True
        rec["qualifies"] = {k: bool(win[k]) and rec["scored"] for k in ("option-check", "project", "none")}
        if rec["scored"] and not win[mode]:
            rec["scored"], rec["why_not"] = False, "not within %d days before to %d after a flood peak (%s list)" % (BEFORE_D, AFTER_D, mode)
        out.append(rec)

    res = {"design": "docs/model_design_flood_run2.md", "check": "pre-run check 1", "built": dt.date.today().isoformat(),
           "peaks": mode, "scored_by_peak_list": {k: sum(r["qualifies"][k] for r in out) for k in ("option-check", "project", "none")},
           "scenes_in_catalogue": len(scenes), "duplicate_entries_dropped": duplicates, "orbits": sorted({(s["orbit"], tuple(s["pols"] or []), s["beam"]) for s in scenes}),
           "rules": {"score_min_cm": SCORE_MIN_CM, "overflow_cm": OVERFLOW_CM, "dry_max_cm": DRY_MAX_CM, "window_days": [-BEFORE_D, AFTER_D],
                     "start_search_h": START_SEARCH_H, "max_gap_h": MAX_GAP_H, "reference_days": REF_DAYS,
                     "reference_cap": REF_CAP, "min_references": MIN_REFS},
           "passes": out}
    with open(os.path.join(c.PROCESSED, "flood_run2_passes.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=list)

    fmt = lambda v, d=0: "–" if v is None else ("%.*f" % (d, v))
    lines = ["# Flood run 2: evening Stripmap passes and dry references", "",
             "Generated by `pipeline/fetch_s1_sm_passes.py` (pre-run check 1 of `docs/model_design_flood_run2.md`).",
             "Catalogue metadata and gauge records only: no radar image has been downloaded or looked at.", "",
             "Candidates: Stripmap scenes on ascending passes over Atibaia town, from %d days before to %d days after" % (BEFORE_D, AFTER_D),
             "a flood peak, with 3E-063 at %d cm or more in the hour of the pass. Event start: the last hour below %d cm," % (SCORE_MIN_CM, OVERFLOW_CM),
             "up to 14 days back. Gaps: the longest run of missing hours from the event start to the pass; more than",
             "%d hours excludes the pass. References: same orbit and polarisation, within %d days, 3E-063 below %d cm," % (MAX_GAP_H, REF_DAYS, DRY_MAX_CM),
             "the %d nearest in time; at least %d needed." % (REF_CAP, MIN_REFS), "",
             "%d Stripmap scenes on ascending passes are in the catalogue over the town from October 2014 to November 2026." % len(scenes), "",
             "Flood peaks: the %s list (the addendum records why). Scored under each list: option check %d, project %d," % (
                 mode, res["scored_by_peak_list"]["option-check"], res["scored_by_peak_list"]["project"]),
             "no peak window %d." % res["scored_by_peak_list"]["none"], "",
             "| Pass (UTC) | Orbit, polarisation | Flood peak | Stage (cm) | Flow (m³/s) | Event start | Gap 62671200 (h) | Gap flow (h) | Dry references | Scored |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in out:
        lines.append("| %s | %s, %s | %s | %s | %s | %s | %s | %s | %d | %s |" % (
            r["pass"].replace("T", " "), r["orbit"], "/".join(r["pols"] or []),
            r["peak_option_check" if mode == "option-check" else "peak_project"] or "–", fmt(r["stage_cm"]), fmt(r["flow_m3s"], 1),
            "%s days before" % r["event_days"] if r["event_days"] is not None else "–", fmt(r["gap_62671200_h"]), fmt(r["gap_3E063_flow_h"]),
            len(r["references"]), "yes" if r["scored"] else "no: " + r["why_not"]))
    n = sum(r["scored"] for r in out)
    lines += ["", "Candidates: **%d**. Scored: **%d** (%d on the HH/HV orbit, %d on the VV/VH orbit)." % (
        len(out), n, sum(r["scored"] and "HH" in (r["pols"] or []) for r in out), sum(r["scored"] and "VV" in (r["pols"] or []) for r in out)), ""]
    with open(os.path.join(c.ROOT, "docs", "flood_run2_passes.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines[12:]))
    print("duplicates dropped:", duplicates, "| scored by peak list:", res["scored_by_peak_list"])


if __name__ == "__main__":
    main()
