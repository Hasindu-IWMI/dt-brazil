"""Flood run 2 event models: the two-stage start (change 1) and the central run.

docs/model_design_flood_run2.md: "The three changes, fixed now" (change 1), "Reach, grid, inputs",
"Test B", and the pre-run addendum (check 2: every event run sets voutput, qoutput and hazard).
Run 1's scripts are imported, not changed and not run.

Each event
  start    the last hour before the pass at which 3E-063 stood below the overflow level (301 cm),
           searched back up to 14 days (the rule pipeline/fetch_s1_sm_passes.py applied).
  stage 1  channel only: every floodplain cell raised 20 m; inflows and downstream level held at the
           start hour's values; 10 days.
  stage 2  the run 2 ground (changes 2 and 3, buildings raised; models/flood_run2/terrain/dem_run2.asc),
           started from stage 1's final depths (startfile) with the floodplain dry and mapped permanent
           water full to its spill level; hourly inflows and downstream levels from the start hour to
           1 hour after the pass; an output every hour (saveint 3600) with voutput, qoutput and hazard.
           Hourly outputs from before 24 hours ahead of the pass are deleted after the run (the design
           keeps 24 hours before to 1 hour after); the maxima are kept.
  inputs   upstream: hourly discharge at 3E-063 as served (QVAR at the upstream channel cell);
           tributaries: run 1's four points, area x (flow at 3E-063 - same-day Cachoeira and Atibainha
           releases) / 431 km2, zero if negative (run 1's rule; the release day is the local day, UTC-3);
           downstream: hourly level at 62671200 through run 1's datum tie (HVAR);
           gaps of up to 3 hours bridged linearly (run 1's rule); a longer gap stops the event.
  the pass the hourly output nearest the middle of the scene's acquisition (start and stop from its id).

Before any event runs, the evening maps and the gate result must be committed (the design: "Made and
committed, with the gate result, before any run 2 event is simulated"). `morning` checks that first.

Usage (atibaia-sfincs environment; LISFLOOD-FP 8.2 in Docker):
  python pipeline/flood_run2_build.py plan              # event windows and inputs; no model run
  python pipeline/flood_run2_build.py morning [jobs]    # the 13 morning passes scored in run 1 (test B)
  python pipeline/flood_run2_build.py summarise         # the records again, from the model folders (no run)
Writes models/flood_run2/events/<pass>/ (not committed) and data/processed/flood_run2_events_morning.json.
"""
import concurrent.futures as cf
import csv
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flood_lisflood_build as lb  # noqa: E402  (run 1's approved setup: reused, not changed)
import flood_run2_terrain as t2  # noqa: E402  (run 2's mapped-water rule and depression filling)

ROOT = lb.ROOT
EVENTS = os.path.join(ROOT, "models", "flood_run2", "events")
DEM_RUN2 = os.path.join(ROOT, "models", "flood_run2", "terrain", "dem_run2.asc")
SUMMARY = os.path.join(lb.PROC, "flood_run2_events_morning.json")
N = 0.020                      # channel n from run 1's calibration (kept, not re-tuned)
OVERFLOW_CM = 301.0
SEARCH_H = 14 * 24             # change 1: look back this far for the last in-bank hour
WARMUP_H = 240                 # stage 1: 10 days
CLOSE_M = 20.0                 # stage 1: floodplain raised this much
MAX_GAP_H = 3
KEEP_BEFORE_H, KEEP_AFTER_H = 24, 1
FREE_KM2 = 1141.0 - 397.0 - 313.0   # land above 3E-063 not behind the two dams: 431 km2
LOCAL = dt.timedelta(hours=-3)
HOUR = dt.timedelta(hours=1)
OUTPUTS = "voutput\nqoutput\nhazard\n"
COMMITTED_FIRST = ["data/processed/flood_run2_observed.json", "data/processed/flood_run2_observed.tif",
                   "docs/flood_run2_observed.png", "docs/model_design_flood_run2.md"]


# ------------------------------------------------------------------ inputs
def hourly(code):
    return {dt.datetime.strptime(k, "%Y-%m-%dT%H:00Z"): v for k, v in lb.hourly(code).items()}


def releases():
    out = {}
    for key in ("cachoeira", "atibainha"):
        with open(os.path.join(lb.PROC, "sar_%s.csv" % key), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["release_m3s"] not in ("", "None"):
                    out.setdefault(r["date"], {})[key] = float(r["release_m3s"])
    return out


def bridged(s, k, t0, t1):
    """Hourly values t0..t1 of field k; gaps of up to MAX_GAP_H hours bridged linearly (neighbours may lie
    outside the window). Returns (values, bridged hours, longest gap)."""
    ok = lambda t: s.get(t) is not None and s[t][k] is not None  # noqa: E731
    vals, n_bridged, longest, run = [], 0, 0, 0
    t = t0
    while t <= t1:
        if ok(t):
            vals.append(s[t][k])
            run = 0
        else:
            run += 1
            longest = max(longest, run)
            a = next((t - i * HOUR for i in range(1, MAX_GAP_H + 1) if ok(t - i * HOUR)), None)
            b = next((t + i * HOUR for i in range(1, MAX_GAP_H + 1) if ok(t + i * HOUR)), None)
            if a is None or b is None or b - a > (MAX_GAP_H + 1) * HOUR:
                raise ValueError("gap over %d hours at %s" % (MAX_GAP_H, t.isoformat()))
            f = (t - a) / (b - a)
            vals.append(s[a][k] + f * (s[b][k] - s[a][k]))
            n_bridged += 1
        t += HOUR
    return vals, n_bridged, longest


def scene_times(item):
    """Start and stop of the acquisition from a Sentinel-1 product id."""
    f = item.split("_")
    a, b = [x for x in f if len(x) == 15 and x[8] == "T"][:2]
    return dt.datetime.strptime(a, "%Y%m%dT%H%M%S"), dt.datetime.strptime(b, "%Y%m%dT%H%M%S")


def morning_passes():
    with open(os.path.join(lb.PROC, "flood_run1_passes.json"), encoding="utf-8") as f:
        return [{"pass": p["pass"], "item": p["item"], "stage_cm_run1": p["stage_cm"]}
                for p in json.load(f)["passes"] if p["scored"]]


def plan_event(p, town, down, rel, offset, tribs):
    a, b = scene_times(p["item"])
    mid = a + (b - a) / 2
    t_out = (mid + dt.timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0)
    t1 = a.replace(minute=0, second=0, microsecond=0)
    start = None
    for k in range(1, SEARCH_H + 1):
        v = town.get(t1 - k * HOUR)
        if v is not None and v[0] is not None and v[0] < OVERFLOW_CM:
            start = t1 - k * HOUR
            break
    if start is None:
        raise ValueError("no in-bank hour within 14 days before %s" % p["pass"])
    end = t_out + HOUR
    q, qb, qgap = bridged(town, 1, start, end)
    lv, lvb, lvgap = bridged(down, 0, start, end)
    hours = [start + i * HOUR for i in range(len(q))]
    trib = []
    for t, qq in zip(hours, q):
        d = (t + LOCAL).date().isoformat()
        r = rel.get(d, {})
        if "cachoeira" not in r or "atibainha" not in r:
            raise ValueError("no release for %s" % d)
        spec = max(0.0, qq - r["cachoeira"] - r["atibainha"]) / FREE_KM2
        trib.append([area * spec for _, area, _ in tribs])
    st = town.get(t1)
    return {"pass": p["pass"], "item": p["item"], "scene_mid_utc": mid.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "output_hour_utc": t_out.strftime("%Y-%m-%dT%H:00Z"), "start_utc": start.strftime("%Y-%m-%dT%H:00Z"),
            "event_days": round((t1 - start).total_seconds() / 86400, 1), "hours": len(hours) - 1,
            "stage_cm_at_pass_hour": None if st is None or st[0] is None else st[0],
            "stage_cm_at_start": town[start][0], "flow_m3s_at_start": round(q[0], 3), "flow_m3s_max": round(max(q), 2),
            "tributary_m3s_max": round(max(sum(x) for x in trib), 2),
            "downstream_m_at_start": round(lv[0] / 100.0 + offset, 3),
            "bridged_hours": {"3E-063_flow": qb, "62671200_level": lvb},
            "longest_gap_h": {"3E-063_flow": qgap, "62671200_level": lvgap},
            "_series": {"t": hours, "q": q, "trib": trib, "down": [v / 100.0 + offset for v in lv]}}


# ------------------------------------------------------------------ model files
def write_inputs(g, out, dem):
    os.makedirs(out, exist_ok=True)
    tr = g["tr"]
    lb.asc(os.path.join(out, "dem.asc"), dem, tr)
    lb.asc(os.path.join(out, "width.asc"), g["width"], tr, fmt="%.1f")
    lb.asc(os.path.join(out, "bank.asc"), g["bank"], tr)
    lb.asc(os.path.join(out, "bed.asc"), g["bed"], tr)
    lb.asc(os.path.join(out, "n.asc"), g["man"], tr, fmt="%.3f")
    xy = lambda cell: (g["x0"] + (cell[0] + 0.5) * lb.DX, g["y1"] - (cell[1] + 0.5) * lb.DX)  # noqa: E731
    with open(os.path.join(out, "run.bci"), "w") as f:
        f.write("P %.1f %.1f QVAR upstream\n" % xy(g["path"][0]))
        for name, _, cell in g["tribs"]:
            f.write("P %.1f %.1f QVAR %s\n" % (xy(cell) + (name,)))
        for r, c in zip(*np.nonzero(g["down"])):
            f.write("P %.1f %.1f HVAR down\n" % xy((c, r)))
    with open(os.path.join(out, "run.stage"), "w") as f:
        f.write("%d\n" % len(g["obs"]))
        for _, cell in g["obs"]:
            f.write("%.1f %.1f\n" % xy(cell))


def write_bdy(g, out, ev, steady):
    s = ev["_series"]
    names = ["upstream"] + [t[0] for t in g["tribs"]]
    with open(os.path.join(out, "run.bdy"), "w") as f:
        f.write("# flood run 2, %s, %s\n" % (ev["pass"], "stage 1 (held at the start hour)" if steady else "stage 2 (hourly)"))
        if steady:
            t_end = WARMUP_H * 3600
            vals = [s["q"][0]] + list(s["trib"][0])
            for name, q in zip(names, vals):
                f.write("%s\n2 seconds\n%.6f 0\n%.6f %d\n" % (name, q / lb.DX, q / lb.DX, t_end))
            f.write("down\n2 seconds\n%.4f 0\n%.4f %d\n" % (s["down"][0], s["down"][0], t_end))
            return
        n = len(s["t"])
        cols = [s["q"]] + [[x[i] for x in s["trib"]] for i in range(len(g["tribs"]))]
        for name, col in zip(names, cols):
            f.write("%s\n%d seconds\n" % (name, n) + "".join("%.6f %d\n" % (v / lb.DX, i * 3600) for i, v in enumerate(col)))
        f.write("down\n%d seconds\n" % n + "".join("%.4f %d\n" % (v, i * 3600) for i, v in enumerate(s["down"])))


def write_par(out, sim_s, saveint, extra=""):
    with open(os.path.join(out, "run.par"), "w") as f:
        f.write("DEMfile dem.asc\nresroot res\ndirroot results\nsim_time %d\ninitial_tstep 1.0\nmassint 3600\n"
                "saveint %d\nmanningfile n.asc\nfpfric 0.035\nbcifile run.bci\nbdyfile run.bdy\nstagefile run.stage\n"
                "acceleration\nSGCn %.4f\nSGCwidth width.asc\nSGCbank bank.asc\nSGCbed bed.asc\nelevoff\n%s"
                % (sim_s, saveint, N, extra))


def read_grid(path):
    return np.loadtxt(path, skiprows=6)


def mass_check(out):
    rows = [ln.split() for ln in open(os.path.join(out, "results", "res.mass")).read().splitlines()[1:] if ln.strip()]
    rows = [[float(v) for v in r] for r in rows]
    vol = max(r[5] for r in rows)
    return {"final_q_in_m3s": round(rows[-1][6], 3), "final_q_out_m3s": round(rows[-1][8], 3),
            "max_abs_volume_error_m3": round(max(abs(r[10]) for r in rows), 3),
            "max_abs_volume_error_fraction_of_peak_volume": float("%.3g" % (max(abs(r[10]) for r in rows) / vol)) if vol else None}


def stage_at(g, out, t_s):
    """Modelled water level (m) at the observation points at time t_s, and the gauge-scale level at 3E-063."""
    data = [ln.split() for ln in open(os.path.join(out, "results", "res.stage")).read().splitlines()]
    data = [[float(v) for v in ln] for ln in data if len(ln) == 1 + len(g["obs"]) and ln[0].replace(".", "", 1).isdigit()]
    row = min(data, key=lambda d: abs(d[0] - t_s))
    beds = [float(g["bed"][cell[1], cell[0]]) for _, cell in g["obs"]]
    wse = [float(d + b) for d, b in zip(row[1:], beds)]
    return wse, float(wse[0] - g["gauge_zero"])


# ------------------------------------------------------------------ one event
def run_event(g, ev, dem2, inside, chan, start_extra, threads):
    tag = ev["pass"].replace(":", "").replace("-", "")
    base = os.path.join(EVENTS, tag)
    t0 = time.time()
    # stage 1: channel only
    s1 = os.path.join(base, "stage1")
    dem1 = dem2.copy()
    dem1[inside] += CLOSE_M
    write_inputs(g, s1, dem1)
    write_bdy(g, s1, ev, steady=True)
    write_par(s1, WARMUP_H * 3600, WARMUP_H * 3600)
    lb.run(s1, threads)
    r1 = lb.read_results(g, s1)
    wd1 = read_grid(os.path.join(s1, "results", "res-0001.wd"))
    # stage 2: the full model from stage 1's channel depths, the floodplain dry, mapped water full
    s2 = os.path.join(base, "stage2")
    write_inputs(g, s2, dem2)
    start = np.where(chan, wd1, 0.0)
    start = np.where(start_extra > 0, start_extra, start)
    lb.asc(os.path.join(s2, "start.wd"), start.astype("float64"), g["tr"], fmt="%.4f")
    write_bdy(g, s2, ev, steady=False)
    sim_h = ev["hours"]
    write_par(s2, sim_h * 3600, 3600, "startfile start.wd\n" + OUTPUTS)
    lb.run(s2, threads)
    # keep the hourly outputs from 24 hours before the pass to 1 hour after
    k_out = output_index(ev)
    removed = 0
    res = os.path.join(s2, "results")
    for fn in os.listdir(res):
        stem = fn.split(".")[0]
        if stem.startswith("res-") and stem[4:].isdigit():
            k = int(stem[4:])
            if not (k_out - KEEP_BEFORE_H <= k <= k_out + KEEP_AFTER_H):
                os.remove(os.path.join(res, fn))
                removed += 1
    return summarise_event(g, ev, inside, removed, round((time.time() - t0) / 60, 1))


def output_index(ev):
    start_t = dt.datetime.strptime(ev["start_utc"], "%Y-%m-%dT%H:00Z")
    t_out = dt.datetime.strptime(ev["output_hour_utc"], "%Y-%m-%dT%H:00Z")
    return int((t_out - start_t) / HOUR)


def summarise_event(g, ev, inside, removed=None, minutes=None):
    """The event's record, read from its model folders (stage 1 and the kept stage 2 outputs)."""
    tag = ev["pass"].replace(":", "").replace("-", "")
    base = os.path.join(EVENTS, tag)
    s1, s2 = os.path.join(base, "stage1"), os.path.join(base, "stage2")
    r1 = lb.read_results(g, s1)
    k_out = output_index(ev)
    res = os.path.join(s2, "results")
    wdfp = read_grid(os.path.join(res, "res-%04d.wdfp" % k_out))
    wse, gauge = stage_at(g, s2, k_out * 3600)
    cell_km2 = lb.DX * lb.DX / 1e6
    rec = {k: v for k, v in ev.items() if not k.startswith("_")}
    rec.update({
        "folder": os.path.relpath(base, ROOT).replace("\\", "/"), "output_index": k_out,
        "stage1": {"days": WARMUP_H / 24, "gauge_scale_m_at_end": round(float(r1["wse"][0] - g["gauge_zero"]), 3),
                   "max_2h_change_cm": round(100 * float(max(r1["change_2h_m"])), 2), "q_in_m3s": round(float(r1["qin"]), 3),
                   "q_out_m3s": round(float(r1["qout"]), 3)},
        "stage2": {"mass": mass_check(s2), "hourly_files_removed": removed,
                   "gauge_scale_m_at_pass_modelled": round(gauge, 3),
                   "gauge_scale_m_at_pass_observed": None if ev["stage_cm_at_pass_hour"] is None else round(ev["stage_cm_at_pass_hour"] / 100.0, 3),
                   "domain_floodplain_over_10cm_km2": round(float(((wdfp > 0.10) & inside).sum()) * cell_km2, 4),
                   "domain_floodplain_over_50cm_km2": round(float(((wdfp >= 0.50) & inside).sum()) * cell_km2, 4)},
        "minutes": minutes})
    with open(os.path.join(base, "event.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)
    return rec


# ------------------------------------------------------------------ main
def committed_first():
    """The design's order: the evening maps and the gate committed before any event runs."""
    bad = []
    for p in COMMITTED_FIRST:
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", p], cwd=ROOT, capture_output=True).returncode == 0
        clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", p], cwd=ROOT).returncode == 0
        if not (tracked and clean):
            bad.append(p)
    return bad


def setup():
    g = lb.build_geometry()
    chan = g["width"] > 0
    dem2 = read_grid(DEM_RUN2)
    assert dem2.shape == (g["H"], g["W"]), dem2.shape
    inside = (dem2 < lb.WALL - 1) & ~chan
    g["dem"] = dem2
    water, _, _ = t2.water_mask(g, inside)
    _, _, _, depth = t2.fill_shallow(dem2, chan, inside, water)
    start_extra = np.where(water, depth, 0.0)
    offset, tie = lb.datum_tie(g)
    town, down, rel = hourly("3E-063"), hourly("62671200"), releases()
    return g, chan, dem2, inside, water, start_extra, offset, tie, town, down, rel


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    assert mode in ("plan", "morning", "summarise"), mode
    if mode == "morning":
        bad = committed_first()
        if bad:
            sys.exit("Not run: commit the evening maps and the gate first (the design's order). Not committed or changed: "
                     + ", ".join(bad))
    g, chan, dem2, inside, water, start_extra, offset, tie, town, down, rel = setup()
    print("ground %s (sha256 %s); mapped water %d cells, %d start full (%.3f km2, median %.2f m deep); datum tie %+.3f m"
          % (os.path.relpath(DEM_RUN2, ROOT), hashlib.sha256(open(DEM_RUN2, "rb").read()).hexdigest()[:16], int(water.sum()),
             int((start_extra > 0).sum()), (start_extra > 0).sum() * lb.DX * lb.DX / 1e6,
             float(np.median(start_extra[start_extra > 0])) if (start_extra > 0).any() else 0.0, offset), flush=True)
    events = [plan_event(p, town, down, rel, offset, g["tribs"]) for p in morning_passes()]
    print("\n pass              stage  start             days  hours  output hour        Q start  Q max  trib max  bridged")
    for e in events:
        print(" %-16s  %5.1f  %s  %4.1f  %5d  %s  %6.1f  %5.1f  %7.1f   %s"
              % (e["pass"], e["stage_cm_at_pass_hour"] or float("nan"), e["start_utc"], e["event_days"], e["hours"],
                 e["output_hour_utc"], e["flow_m3s_at_start"], e["flow_m3s_max"], e["tributary_m3s_max"], e["bridged_hours"]))
    if mode == "plan":
        return
    recs = {}

    def report(r):
        recs[r["pass"]] = r
        s2 = r["stage2"]
        print("  %s: gauge %.2f m modelled, %.2f observed; floodplain over 0.5 m %.3f km2 (domain); volume error %s"
              % (r["pass"], s2["gauge_scale_m_at_pass_modelled"], s2["gauge_scale_m_at_pass_observed"] or float("nan"),
                 s2["domain_floodplain_over_50cm_km2"], s2["mass"]["max_abs_volume_error_fraction_of_peak_volume"]), flush=True)

    if mode == "summarise":
        # records only, from the model folders already run (no model is run)
        for e in events:
            report(summarise_event(g, e, inside))
    else:
        jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        threads = max(1, 30 // jobs)
        with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
            futs = {ex.submit(run_event, g, e, dem2, inside, chan, start_extra, threads): e["pass"] for e in events}
            for fu in cf.as_completed(futs):
                report(fu.result())
    out = {"design": "docs/model_design_flood_run2.md", "what": "test B events: the 13 morning passes scored in run 1, central run",
           "built": dt.date.today().isoformat(), "ground_sha256": hashlib.sha256(open(DEM_RUN2, "rb").read()).hexdigest(),
           "channel_n": N, "datum_tie": tie, "mapped_water_start_full_cells": int((start_extra > 0).sum()),
           "rules": {"overflow_cm": OVERFLOW_CM, "search_back_h": SEARCH_H, "stage1_days": WARMUP_H / 24,
                     "stage1_floodplain_raised_m": CLOSE_M, "max_gap_bridged_h": MAX_GAP_H, "outputs": OUTPUTS.split(),
                     "kept_hours": [-KEEP_BEFORE_H, KEEP_AFTER_H], "tributary_free_area_km2": FREE_KM2,
                     "release_day": "local day (UTC-3) of the hour"},
           "events": [recs[e["pass"]] for e in events]}
    with open(SUMMARY, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("wrote", os.path.relpath(SUMMARY, ROOT))


if __name__ == "__main__":
    main()
