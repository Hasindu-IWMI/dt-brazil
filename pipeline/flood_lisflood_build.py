"""LISFLOOD-FP 8.2 model of flood run 1: build, steady test and channel-roughness calibration.

docs/model_design_flood_run1.md, "LISFLOOD-FP setup (approved 17 November 2026)".
Uses no radar image and no observed flood extent. Run with the atibaia-sfincs
environment (rasterio, shapely, pyproj); LISFLOOD-FP runs in Docker
(atibaia/lisflood-fp:8.2, envs/lisflood-fp.Dockerfile).

Inputs (all produced earlier in the pipeline):
  models/flood_run1/terrain/domain.gpkg, buildings.gpkg  (pipeline/flood_build_model.py)
  data/raw/dem/anadem_window.*, data/raw/worldcover/worldcover_flood_run1.*
  data/processed/flood_run1_channel.csv (isotonic bank, bed), flood_run1_tributaries.json
  data/processed/flood_hourly_3E-063.csv, flood_hourly_62671200.csv

Model (approved setup)
  20 m cells, EPSG:31983, over the domain; outside it a wall.
  Ground: ANADEM resampled bilinearly. Buildings: cells at least half covered
  by footprints raised 10 m (5 m supersampling).
  Channel: a 4-connected path of cells along the OSM line from 1.5 km above
  3E-063 to station 62671200; SGCwidth 11 m; SGCbank = isotonic bank at the
  cell's position along the line; SGCbed = bank - 2.11 m; the cell's ground
  set to the bank. SGCn = the channel roughness.
  Floodplain roughness: WorldCover majority class per cell -> design table.
  Inflows: QVAR at the upstream channel cell and the four tributary channel
  cells, as discharge / 20 m (LISFLOOD-FP takes flow per unit width).
  Downstream: HVAR on the domain's last cells across the valley at the station.

Datum tie at 62671200 (approved): the station's median observed level equals
the station's bed plus the median depth at 3E-063 (stage - 0.90 m), over the
hours both stations report, 2015-2026.

Steady runs (steady test and calibration): constant inflow at the upstream
cell, no tributary flow, downstream level = the median observed station level
in the hours when 3E-063 carried that flow (+/- 10%), through the datum tie.
That way of setting the steady downstream level is an implementation detail
recorded in the addendum.

Usage:
  python pipeline/flood_lisflood_build.py steady            # 15 m3/s, n = 0.035
  python pipeline/flood_lisflood_build.py calibrate         # n 0.020-0.080 x Q 5, 10, 15
"""
import concurrent.futures as cf
import csv
import json
import math
import os
import statistics
import subprocess
import sys

import geopandas as gpd
import numpy as np
import rasterio
import shapely
from rasterio import features
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flood_build_model as fb  # noqa: E402  (river line, gauge positions, roughness table)

ROOT, RAW, PROC = fb.ROOT, fb.RAW, fb.PROC
IMAGE = "atibaia/lisflood-fp:8.2"
EPSG, DX, SUP = 31983, 20.0, 4               # model cell, 5 m supersampling for buildings and land cover
WIDTH, DEPTH, LIFT = 11.0, 2.11, 10.0
WALL = 900.0                                  # ground outside the domain
OVERFLOW_M, H0_M = 3.01, 0.90
RATING = lambda q: H0_M + (q / 7.8) ** (1 / 1.1)   # SP Aguas' last low-flow rating at 3E-063 (gauge scale, m)
TERR = os.path.join(ROOT, "models", "flood_run1", "terrain")
BASE = os.path.join(ROOT, "models", "flood_run1", "lisflood")


def asc(path, a, tr, nodata=-9999.0, fmt="%.3f"):
    H, W = a.shape
    with open(path, "w") as f:
        f.write("ncols %d\nnrows %d\nxllcorner %.3f\nyllcorner %.3f\ncellsize %g\nNODATA_value %g\n"
                % (W, H, tr.c, tr.f - H * DX, DX, nodata))
        for row in a:
            f.write(" ".join(fmt % v for v in row) + "\n")


def hourly(code):
    out = {}
    for r in csv.DictReader(open(os.path.join(PROC, "flood_hourly_%s.csv" % code), encoding="utf-8")):
        lv = float(r["level_cm"]) if r["level_cm"] not in ("", "None") else None
        q = float(r["discharge_m3s"]) if r["discharge_m3s"] not in ("", "None") else None
        out[r["hour_utc"]] = (lv, q)
    return out


def build_geometry():
    """Grid, rasters and points shared by every run. Returns a dict."""
    line, _ = fb.river_line_utm()
    s_gauge, s_station = line.project(fb.utm_point(*fb.GAUGE)), line.project(fb.utm_point(*fb.STATION))
    rows = list(csv.DictReader(open(os.path.join(PROC, "flood_run1_channel.csv"), encoding="utf-8")))
    s_prof = np.array([line.project(fb.utm_point(float(r["lat"]), float(r["lon"]))) for r in rows])
    bank_prof = np.array([float(r["bank"]) for r in rows])
    o = np.argsort(s_prof)
    s_prof, bank_prof = s_prof[o], bank_prof[o]
    s_start = s_prof[0]
    dom = gpd.read_file(os.path.join(TERR, "domain.gpkg")).geometry.iloc[0]
    minx, miny, maxx, maxy = dom.bounds
    x0, y0 = math.floor((minx - 60) / DX) * DX, math.floor((miny - 60) / DX) * DX
    x1, y1 = math.ceil((maxx + 60) / DX) * DX, math.ceil((maxy + 60) / DX) * DX
    W, H = int(round((x1 - x0) / DX)), int(round((y1 - y0) / DX))
    tr = from_origin(x0, y1, DX, DX)
    tr5 = from_origin(x0, y1, DX / SUP, DX / SUP)
    inside = features.rasterize([(dom, 1)], out_shape=(H, W), transform=tr, all_touched=False, dtype="uint8").astype(bool)

    # ground: ANADEM bilinear
    meta = json.load(open(os.path.join(RAW, "dem", "anadem_window.json"), encoding="utf-8"))
    bb = meta["bbox"]
    z = np.fromfile(os.path.join(RAW, "dem", "anadem_window.f32"), dtype="<f4").reshape(meta["height"], meta["width"])
    trz = from_origin(bb["west"], bb["north"], (bb["east"] - bb["west"]) / meta["width"], (bb["north"] - bb["south"]) / meta["height"])
    dem = np.full((H, W), np.nan, dtype="float32")
    reproject(z.astype("float32"), dem, src_transform=trz, src_crs="EPSG:4326", dst_transform=tr, dst_crs=f"EPSG:{EPSG}",
              resampling=Resampling.bilinear, src_nodata=-9999.0, dst_nodata=np.nan)

    # channel path: 4-connected cells along the line
    path, seen, revisits = [], {}, 0
    for s in np.arange(s_start, s_station + 1e-6, 2.0):
        p = line.interpolate(s)
        c, r = int((p.x - x0) // DX), int((y1 - p.y) // DX)
        if path and path[-1][:2] == (c, r):
            continue
        if path:
            pc, pr = path[-1][:2]
            if pc != c and pr != r:  # diagonal step: go through the corner cell first
                if (c, pr) not in seen:
                    path.append((c, pr, s))
                    seen[(c, pr)] = len(path) - 1
        if (c, r) in seen:
            revisits += 1
            continue
        path.append((c, r, s))
        seen[(c, r)] = len(path) - 1
    width = np.zeros((H, W), dtype="float32")
    bank = dem.copy()
    bed = dem.copy()
    for c, r, s in path:
        b = float(np.interp(s, s_prof, bank_prof))
        width[r, c], bank[r, c], bed[r, c] = WIDTH, b, b - DEPTH
        dem[r, c] = b
    chan = width > 0
    # channel cells adjacent but not consecutive along the path (cut-offs the model may use)
    order = {(c, r): k for k, (c, r, _) in enumerate(path)}
    shortcuts = sum(1 for (c, r), k in order.items() for dc, dr in ((1, 0), (0, 1))
                    if (c + dc, r + dr) in order and abs(order[(c + dc, r + dr)] - k) > 1)

    # buildings: fraction of each cell from 5 m supersampling
    blds = gpd.read_file(os.path.join(TERR, "buildings.gpkg")).geometry
    b5 = features.rasterize([(g, 1) for g in blds], out_shape=(H * SUP, W * SUP), transform=tr5, all_touched=False, dtype="uint8")
    frac = b5.reshape(H, SUP, W, SUP).mean(axis=(1, 3))
    bcells = (frac >= 0.5) & ~chan & inside
    dem[bcells] += LIFT

    # floodplain roughness: majority WorldCover class
    wm = json.load(open(os.path.join(RAW, "worldcover", "worldcover_flood_run1.json"), encoding="utf-8"))
    wc = np.fromfile(os.path.join(RAW, "worldcover", "worldcover_flood_run1.u8"), dtype="u1").reshape(wm["height"], wm["width"])
    cls5 = np.zeros((H * SUP, W * SUP), dtype="uint8")
    reproject(wc, cls5, src_transform=from_origin(wm["west"], wm["north"], wm["pixel_deg"], wm["pixel_deg"]), src_crs="EPSG:4326",
              dst_transform=tr5, dst_crs=f"EPSG:{EPSG}", resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
    blocks = cls5.reshape(H, SUP, W, SUP).transpose(0, 2, 1, 3).reshape(H, W, SUP * SUP)
    man = np.full((H, W), 0.035, dtype="float32")
    for i in range(H):
        for j in range(W):
            v = blocks[i, j]
            v = v[v > 0]
            if v.size:
                man[i, j] = fb.MANNING.get(int(np.bincount(v).argmax()), 0.035)

    # outside the domain: a wall
    dem[~inside & ~chan] = WALL
    dem = np.where(np.isfinite(dem), dem, WALL)

    # downstream boundary cells: domain cells whose position along the line is within 20 m of the station
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    cx, cy = tr * (jj + 0.5, ii + 0.5)
    s_cell = shapely.line_locate_point(line, shapely.points(cx.ravel(), cy.ravel())).reshape(H, W)
    dist = shapely.distance(line, shapely.points(cx.ravel(), cy.ravel())).reshape(H, W)
    down = (inside | chan) & (s_cell >= s_station - 20.0) & (dem < WALL)
    last = path[-1]
    down[last[1], last[0]] = True

    def path_cell(s):
        return min(path, key=lambda p: abs(p[2] - s))

    tribs = []
    for t in json.load(open(os.path.join(PROC, "flood_run1_tributaries.json"), encoding="utf-8"))["points"]:
        s_t = line.project(fb.utm_point(t["lat"], t["lon"]))
        if s_t < s_station - 1.0:
            tribs.append(("trib%d" % len(tribs), t["area_km2"], path_cell(s_t)))
    obs = [("gauge_3E-063", path_cell(s_gauge)), ("km1", path_cell(s_gauge + 1000)), ("km3", path_cell(s_gauge + 3000)),
           ("km5", path_cell(s_gauge + 5000)), ("near_station", path_cell(s_station - 100))]
    bank_gauge = float(np.interp(s_gauge, s_prof, bank_prof))
    return {"line": line, "tr": tr, "W": W, "H": H, "dem": dem, "bank": bank, "bed": bed, "width": width, "man": man,
            "path": path, "revisits": revisits, "shortcuts": shortcuts, "bcells": int(bcells.sum()), "down": down,
            "tribs": tribs, "obs": obs, "s_gauge": s_gauge, "s_station": s_station, "x0": x0, "y1": y1,
            "gauge_zero": bank_gauge - OVERFLOW_M, "bed_station": float(bed[last[1], last[0]]),
            "inside": int(inside.sum())}


def datum_tie(g):
    """Offset (m) turning 62671200's level (cm/100) into an elevation, by the approved rule."""
    town, st = hourly("3E-063"), hourly("62671200")
    common = [h for h in town if town[h][0] is not None and h in st and st[h][0] is not None]
    depth = statistics.median(town[h][0] / 100.0 - H0_M for h in common)
    med_st = statistics.median(st[h][0] / 100.0 for h in common)
    offset = g["bed_station"] + depth - med_st
    return offset, {"common_hours": len(common), "median_depth_at_3E-063_m": round(depth, 3),
                    "median_level_62671200_m": round(med_st, 3), "offset_m": round(offset, 3)}


def steady_down_level(g, offset, q):
    town, st = hourly("3E-063"), hourly("62671200")
    lv = [st[h][0] / 100.0 for h in town if town[h][1] is not None and abs(town[h][1] - q) <= 0.1 * q
          and h in st and st[h][0] is not None]
    return statistics.median(lv) + offset, len(lv)


def write_run(g, out, n, q_up, down_level, hours):
    os.makedirs(out, exist_ok=True)
    tr = g["tr"]
    asc(os.path.join(out, "dem.asc"), g["dem"], tr)
    asc(os.path.join(out, "width.asc"), g["width"], tr, fmt="%.1f")
    asc(os.path.join(out, "bank.asc"), g["bank"], tr)
    asc(os.path.join(out, "bed.asc"), g["bed"], tr)
    asc(os.path.join(out, "n.asc"), g["man"], tr, fmt="%.3f")
    xy = lambda cell: (g["x0"] + (cell[0] + 0.5) * DX, g["y1"] - (cell[1] + 0.5) * DX)
    t_end = hours * 3600
    with open(os.path.join(out, "run.bci"), "w") as f:
        f.write("P %.1f %.1f QVAR upstream\n" % xy(g["path"][0]))
        for name, _, cell in g["tribs"]:
            f.write("P %.1f %.1f QVAR %s\n" % (xy(cell) + (name,)))
        for r, c in zip(*np.nonzero(g["down"])):
            f.write("P %.1f %.1f HVAR down\n" % xy((c, r)))
    with open(os.path.join(out, "run.bdy"), "w") as f:
        f.write("# steady run\n")
        for name, q in [("upstream", q_up)] + [(t[0], 0.0) for t in g["tribs"]]:
            f.write("%s\n2 seconds\n%.6f 0\n%.6f %d\n" % (name, q / DX, q / DX, t_end))
        f.write("down\n2 seconds\n%.4f 0\n%.4f %d\n" % (down_level, down_level, t_end))
    with open(os.path.join(out, "run.stage"), "w") as f:
        f.write("%d\n" % len(g["obs"]))
        for _, cell in g["obs"]:
            f.write("%.1f %.1f\n" % xy(cell))
    with open(os.path.join(out, "run.par"), "w") as f:
        f.write("DEMfile dem.asc\nresroot res\ndirroot results\nsim_time %d\ninitial_tstep 1.0\nmassint 3600\n"
                "saveint %d\nmanningfile n.asc\nfpfric 0.035\nbcifile run.bci\nbdyfile run.bdy\nstagefile run.stage\n"
                "acceleration\nSGCn %.4f\nSGCwidth width.asc\nSGCbank bank.asc\nSGCbed bed.asc\nelevoff\n" % (t_end, t_end, n))


def run(out, threads=None):
    cmd = ["docker", "run", "--rm"] + (["-e", "OMP_NUM_THREADS=%d" % threads] if threads else []) + \
          ["-v", out.replace("\\", "/") + ":/data", IMAGE, "run.par"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
    if r.returncode != 0:
        raise RuntimeError("LISFLOOD-FP failed in %s: %s" % (out, r.stderr[-800:] or r.stdout[-800:]))


def read_results(g, out):
    mass = [ln.split() for ln in open(os.path.join(out, "results", "res.mass")).read().splitlines()[1:] if ln.strip()]
    qin, qout = float(mass[-1][6]), float(mass[-1][8])
    data = [ln.split() for ln in open(os.path.join(out, "results", "res.stage")).read().splitlines()]
    data = [[float(v) for v in ln] for ln in data if len(ln) == 1 + len(g["obs"]) and ln[0].replace(".", "", 1).isdigit()]
    t = np.array([d[0] for d in data])
    dep = np.array([d[1:] for d in data])
    beds = [g["bed"][cell[1], cell[0]] for _, cell in g["obs"]]
    wse = dep + np.array(beds)
    last = t >= t[-1] - 7200
    change = (wse[last].max(axis=0) - wse[last].min(axis=0)).tolist()
    return {"qin": qin, "qout": qout, "wse": wse[-1].tolist(), "change_2h_m": change, "names": [o[0] for o in g["obs"]]}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "steady"
    g = build_geometry()
    offset, tie = datum_tie(g)
    print("grid %d x %d (20 m), %d cells inside the domain; channel path %d cells (%d revisits skipped, %d cut-offs "
          "between adjacent non-consecutive cells); %d cells raised as buildings; %d downstream boundary cells; tributaries %s"
          % (g["W"], g["H"], g["inside"], len(g["path"]), g["revisits"], g["shortcuts"], g["bcells"], int(g["down"].sum()),
             [(t[0], t[1]) for t in g["tribs"]]), flush=True)
    print("gauge zero %.2f m; bed at the station %.2f m; datum tie %s" % (g["gauge_zero"], g["bed_station"], tie), flush=True)
    os.makedirs(BASE, exist_ok=True)
    json.dump({"datum_tie": tie, "gauge_zero_m": round(g["gauge_zero"], 3), "bed_station_m": round(g["bed_station"], 3),
               "path_cells": len(g["path"]), "cutoffs": g["shortcuts"], "building_cells": g["bcells"]},
              open(os.path.join(BASE, "geometry_summary.json"), "w"), indent=1)

    if mode == "steady":
        q, n, hours = 15.0, 0.035, int(sys.argv[2]) if len(sys.argv) > 2 else 72
        lvl, nh = steady_down_level(g, offset, q)
        out = os.path.join(BASE, "steady_15")
        write_run(g, out, n, q, lvl, hours)
        print("steady test: 15 m3/s, n %.3f, downstream level %.2f m (median of %d hours), %d h" % (n, lvl, nh, hours), flush=True)
        run(out)
        res = read_results(g, out)
        for name, z, dz in zip(res["names"], res["wse"], res["change_2h_m"]):
            print("  %-13s level %.3f m (last 2 h change %.1f cm)" % (name, z, 100 * dz))
        stage = res["wse"][0] - g["gauge_zero"]
        print("  Q in %.2f, out %.2f m3/s | gauge scale at 3E-063: %.2f m (rating: %.2f m)" % (res["qin"], res["qout"], stage, RATING(q)))
        ok = max(res["change_2h_m"]) < 0.01 and abs(res["qout"] - res["qin"]) < 0.05 * res["qin"]
        print("STEADY TEST", "PASSED" if ok else "FAILED")
        sys.exit(0 if ok else 1)

    if mode == "calibrate":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 72
        ns = [round(0.020 + 0.005 * k, 3) for k in range(13)]
        qs = [5.0, 10.0, 15.0]
        levels = {q: steady_down_level(g, offset, q) for q in qs}
        for q in qs:
            print("  Q %4.1f: downstream level %.2f m (median of %d hours); target stage %.2f m" % (q, levels[q][0], levels[q][1], RATING(q)))
        jobs = []
        for n in ns:
            for q in qs:
                out = os.path.join(BASE, "calib", "n%.3f_q%02d" % (n, q))
                write_run(g, out, n, q, levels[q][0], hours)
                jobs.append((n, q, out))
        results = {}
        with cf.ThreadPoolExecutor(max_workers=6) as ex:
            futs = {ex.submit(run, out, 5): (n, q, out) for n, q, out in jobs}
            for fu in cf.as_completed(futs):
                n, q, out = futs[fu]
                fu.result()
                res = read_results(g, out)
                results[(n, q)] = res
                print("  done n %.3f Q %4.1f: stage %.2f m (target %.2f), max 2 h change %.1f cm, Q out %.2f"
                      % (n, q, res["wse"][0] - g["gauge_zero"], RATING(q), 100 * max(res["change_2h_m"]), res["qout"]), flush=True)
        table = []
        for n in ns:
            errs = [results[(n, q)]["wse"][0] - g["gauge_zero"] - RATING(q) for q in qs]
            rmse = math.sqrt(sum(e * e for e in errs) / len(errs))
            table.append({"n": n, "errors_m": [round(e, 3) for e in errs], "rmse_m": round(rmse, 3),
                          "max_change_2h_cm": round(100 * max(max(results[(n, q)]["change_2h_m"]) for q in qs), 2)})
        best = min(table, key=lambda r: r["rmse_m"])
        json.dump({"targets_m": {str(q): round(RATING(q), 3) for q in qs}, "downstream_levels_m": {str(q): round(levels[q][0], 3) for q in qs},
                   "table": table, "chosen": best}, open(os.path.join(BASE, "calibration.json"), "w"), indent=1)
        print("\n  n      errors at 5 / 10 / 15 m3/s (m)    RMSE")
        for r in table:
            print("  %.3f  %+.2f / %+.2f / %+.2f            %.3f%s" % (r["n"], *r["errors_m"], r["rmse_m"], "  <- chosen" if r is best else ""))
        if best["n"] in (ns[0], ns[-1]):
            print("  NOTE: the chosen n is on the edge of the range")


if __name__ == "__main__":
    main()
