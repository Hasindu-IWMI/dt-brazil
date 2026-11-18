"""Pre-run check 3 of flood run 2 (docs/model_design_flood_run2.md): the terrain changes, and the
in-bank re-check. No observed flood map and no radar image is used.

Starts from run 1's approved LISFLOOD-FP geometry (pipeline/flood_lisflood_build.py, imported, not
changed): 20 m cells, EPSG:31983, ANADEM bilinear, the 566-cell channel path, isotonic bank,
bed = bank - 2.11 m. On the bare ground (before buildings are raised 10 m):

  Change 2: a floodplain cell not mapped as water whose ground lies below the ordinary river level at
            its nearest channel cell (bank - 0.82 m; nearest along the domain's cells, 4-connected) is
            raised to that level.
  Change 3: closed depressions (outlets: the channel cells at bank level and the domain's edge) no
            deeper than 1.5 m below their spill level are filled to it; deeper ones are kept and listed.
            Mapped water is not filled.
  Mapped water: cells whose WorldCover 2021 majority class is 80 or 90, and OSM water polygons in
            web/public/data/vectors.json that fall in the domain.

Then the steady tests at 5, 10 and 15 m3/s with n = 0.020, as calibrated (72 hours, the calibration's
downstream levels). Passes if the stage at 3E-063 is within 2 cm of the calibration's at every flow,
and the floodplain holds at most 0.05 km2 of water over 10 cm at every flow.

Run with the atibaia-sfincs environment (rasterio, geopandas, shapely, scipy); LISFLOOD-FP in Docker.
Usage: python pipeline/flood_run2_terrain.py
Writes models/flood_run2/terrain/ (ground grids, steady runs; not committed),
data/processed/flood_run2_terrain.json.
"""
import collections
import concurrent.futures as cf
import heapq
import json
import os
import sys

import geopandas as gpd
import numpy as np
import shapely
from rasterio import features
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flood_lisflood_build as lb  # noqa: E402  (run 1's approved model setup: reused, not changed)

ROOT = lb.ROOT
OUT = os.path.join(ROOT, "models", "flood_run2", "terrain")
ORDINARY_BELOW_BANK = 2.11 - 1.29  # bed below bank, minus the median depth at 3E-063: 0.82 m
FILL_MAX = 1.5
N = 0.020
QS = (5.0, 10.0, 15.0)
HOURS = 72
WET_M, WET_MAX_KM2, STAGE_TOL_M = 0.10, 0.05, 0.02


def water_mask(g, inside):
    """WorldCover 80/90 majority cells, plus OSM water polygons, inside the domain."""
    H, W, DX, SUP = g["H"], g["W"], lb.DX, lb.SUP
    wm = json.load(open(os.path.join(lb.RAW, "worldcover", "worldcover_flood_run1.json"), encoding="utf-8"))
    wc = np.fromfile(os.path.join(lb.RAW, "worldcover", "worldcover_flood_run1.u8"), dtype="u1").reshape(wm["height"], wm["width"])
    cls5 = np.zeros((H * SUP, W * SUP), dtype="uint8")
    tr5 = from_origin(g["x0"], g["y1"], DX / SUP, DX / SUP)
    reproject(wc, cls5, src_transform=from_origin(wm["west"], wm["north"], wm["pixel_deg"], wm["pixel_deg"]), src_crs="EPSG:4326",
              dst_transform=tr5, dst_crs="EPSG:%d" % lb.EPSG, resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
    blocks = cls5.reshape(H, SUP, W, SUP).transpose(0, 2, 1, 3).reshape(H, W, SUP * SUP)
    wc_water = np.zeros((H, W), bool)
    for i in range(H):
        for j in range(W):
            v = blocks[i, j]
            v = v[v > 0]
            if v.size and int(np.bincount(v).argmax()) in (80, 90):
                wc_water[i, j] = True
    vec = json.load(open(os.path.join(ROOT, "web", "public", "data", "vectors.json"), encoding="utf-8"))
    polys = []
    for w in vec["waters"]:
        for ring in w["rings"]:
            if len(ring) >= 4:
                polys.append(shapely.Polygon(ring))
    osm = np.zeros((H, W), bool)
    if polys:
        gs = gpd.GeoSeries(polys, crs="EPSG:4326").to_crs("EPSG:%d" % lb.EPSG)
        osm = features.rasterize([(p, 1) for p in gs if p.is_valid and not p.is_empty], out_shape=(H, W), transform=g["tr"],
                                 all_touched=False, dtype="uint8").astype(bool)
    return (wc_water | osm) & inside, int((wc_water & inside).sum()), int((osm & inside).sum())


def building_cells(g, chan, inside):
    """Run 1's rule: cells at least half covered by footprints (5 m supersampling), not channel, inside."""
    H, W, DX, SUP = g["H"], g["W"], lb.DX, lb.SUP
    blds = gpd.read_file(os.path.join(lb.TERR, "buildings.gpkg")).geometry
    b5 = features.rasterize([(b, 1) for b in blds], out_shape=(H * SUP, W * SUP), transform=from_origin(g["x0"], g["y1"], DX / SUP, DX / SUP),
                            all_touched=False, dtype="uint8")
    return (b5.reshape(H, SUP, W, SUP).mean(axis=(1, 3)) >= 0.5) & ~chan & inside


def nearest_channel_bank(bank, chan, inside):
    """Bank of the nearest channel cell, by 4-connected steps through the domain (multi-source BFS)."""
    H, W = chan.shape
    near = np.full((H, W), np.nan)
    q = collections.deque()
    for r, c in zip(*np.nonzero(chan)):
        near[r, c] = bank[r, c]
        q.append((r, c))
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and inside[rr, cc] and np.isnan(near[rr, cc]):
                near[rr, cc] = near[r, c]
                q.append((rr, cc))
    return near


def fill_shallow(z, chan, inside, water):
    """Priority-flood from the outlets (channel cells, domain edge); fill depressions no deeper than
    FILL_MAX, not mapped water. Returns the new ground and the depressions (kept and filled)."""
    H, W = z.shape
    spill = np.full((H, W), np.nan)
    pq = []
    edge = np.zeros((H, W), bool)
    for r in range(H):
        for c in range(W):
            if not inside[r, c] and not chan[r, c]:
                continue
            out = chan[r, c] or any(not (0 <= r + dr < H and 0 <= c + dc < W) or not (inside[r + dr, c + dc] or chan[r + dr, c + dc])
                                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if out:
                edge[r, c] = True
                spill[r, c] = z[r, c]
                heapq.heappush(pq, (z[r, c], r, c))
    while pq:
        h, r, c = heapq.heappop(pq)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and (inside[rr, cc] or chan[rr, cc]) and np.isnan(spill[rr, cc]):
                spill[rr, cc] = max(z[rr, cc], h)
                heapq.heappush(pq, (spill[rr, cc], rr, cc))
    depth = np.where(np.isnan(spill), 0.0, spill - z)
    hollow = (depth > 0.001) & inside & ~chan
    # depressions: 4-connected groups of hollow cells
    label = np.zeros((H, W), int)
    groups = []
    for r, c in zip(*np.nonzero(hollow)):
        if label[r, c]:
            continue
        k = len(groups) + 1
        cells, q = [], collections.deque([(r, c)])
        label[r, c] = k
        while q:
            a, b = q.popleft()
            cells.append((a, b))
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                aa, bb = a + dr, b + dc
                if 0 <= aa < H and 0 <= bb < W and hollow[aa, bb] and not label[aa, bb]:
                    label[aa, bb] = k
                    q.append((aa, bb))
        groups.append(cells)
    new = z.copy()
    filled, kept = [], []
    for cells in groups:
        rr, cc = np.array(cells).T
        dmax = float(depth[rr, cc].max())
        rec = {"cells": len(cells), "area_km2": round(len(cells) * lb.DX * lb.DX / 1e6, 4), "max_depth_m": round(dmax, 2),
               "spill_m": round(float(spill[rr, cc].max()), 2), "water_cells": int(water[rr, cc].sum())}
        if dmax <= FILL_MAX:
            keep_water = water[rr, cc]
            new[rr[~keep_water], cc[~keep_water]] = spill[rr[~keep_water], cc[~keep_water]]
            filled.append(rec)
        else:
            rec["centre_cell_col_row"] = [int(np.median(cc)), int(np.median(rr))]
            kept.append(rec)
    return new, filled, kept, depth


def main():
    os.makedirs(OUT, exist_ok=True)
    lb.LIFT = 0.0  # bare ground: buildings are raised after the changes
    g = lb.build_geometry()
    chan = g["width"] > 0
    inside = (g["dem"] < lb.WALL - 1) & ~chan
    ground = g["dem"].copy()
    water, n_wc, n_osm = water_mask(g, inside)
    bcells = building_cells(g, chan, inside)

    # ---- change 2
    near = nearest_channel_bank(g["bank"], chan, inside | chan)
    ordinary = near - ORDINARY_BELOW_BANK
    raise2 = inside & ~water & np.isfinite(ordinary) & (ground < ordinary)
    g2 = np.where(raise2, ordinary, ground)
    # ---- change 3
    g3, filled, kept, depth_before = fill_shallow(g2, chan, inside, water)
    raise3 = (g3 - g2) > 0.001
    # report on run 1's ground too: the depressions before any change
    _, filled1, kept1, _ = fill_shallow(ground, chan, inside, water)

    cell_km2 = lb.DX * lb.DX / 1e6
    rep = {
        "design": "docs/model_design_flood_run2.md", "check": "pre-run check 3",
        "domain_cells": int(inside.sum()), "channel_cells": int(chan.sum()), "building_cells": int(bcells.sum()),
        "mapped_water": {"cells": int(water.sum()), "km2": round(water.sum() * cell_km2, 3), "worldcover_cells": n_wc, "osm_cells": n_osm},
        "change_2": {"cells": int(raise2.sum()), "km2": round(raise2.sum() * cell_km2, 3),
                     "median_raise_m": round(float(np.median((g2 - ground)[raise2])), 2) if raise2.any() else 0,
                     "p90_raise_m": round(float(np.percentile((g2 - ground)[raise2], 90)), 2) if raise2.any() else 0},
        "change_3": {"depressions_filled": len(filled), "filled_km2": round(sum(f["area_km2"] for f in filled), 3),
                     "cells_raised": int(raise3.sum()), "median_raise_m": round(float(np.median((g3 - g2)[raise3])), 2) if raise3.any() else 0,
                     "deep_depressions_kept": len(kept), "kept_km2": round(sum(k["area_km2"] for k in kept), 3),
                     "kept": sorted(kept, key=lambda k: -k["area_km2"])},
        "run1_ground_depressions": {"shallow_km2": round(sum(f["area_km2"] for f in filled1), 3),
                                    "deep_km2": round(sum(k["area_km2"] for k in kept1), 3), "count": len(filled1) + len(kept1)},
    }
    print(json.dumps({k: v for k, v in rep.items() if k != "change_3"}, indent=1))
    print("change 3:", {k: v for k, v in rep["change_3"].items() if k != "kept"})

    # ---- the ground run 2 uses: changes 2 and 3, buildings raised, the wall outside
    dem = g3.copy()
    dem[bcells] += 10.0
    dem[~inside & ~chan] = lb.WALL
    np.save(os.path.join(OUT, "ground_run2.npy"), g3)
    lb.asc(os.path.join(OUT, "dem_run2.asc"), dem, g["tr"])
    lb.asc(os.path.join(OUT, "change.asc"), (g3 - ground).astype("float32"), g["tr"])

    # ---- steady tests on the new ground, n = 0.020, as calibrated
    gg = dict(g)
    gg["dem"] = dem
    calib = json.load(open(os.path.join(lb.BASE, "calibration.json"), encoding="utf-8"))
    row = next(r for r in calib["table"] if abs(r["n"] - N) < 1e-9)
    jobs = []
    for q in QS:
        lvl = float(calib["downstream_levels_m"][str(q)])
        out = os.path.join(OUT, "steady_q%02d" % q)
        lb.write_run(gg, out, N, q, lvl, HOURS)
        jobs.append((q, out))
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(lambda j: lb.run(j[1], 5), jobs))
    steady = []
    for (q, out), err_cal in zip(jobs, row["errors_m"]):
        res = lb.read_results(gg, out)
        stage = res["wse"][0] - g["gauge_zero"]
        err = stage - lb.RATING(q)
        wd = np.loadtxt(os.path.join(out, "results", "res-0001.wd"), skiprows=6)
        wet = (wd > WET_M) & inside
        steady.append({"q_m3s": q, "stage_m": round(stage, 3), "error_m": round(err, 3), "calibration_error_m": err_cal,
                       "difference_m": round(err - err_cal, 3), "floodplain_wet_km2": round(wet.sum() * cell_km2, 4),
                       "q_out_m3s": round(res["qout"], 2), "max_2h_change_cm": round(100 * max(res["change_2h_m"]), 2)})
        print("Q %4.1f: stage %.2f m, error %+.3f m (calibration %+.3f), floodplain over 10 cm %.4f km2"
              % (q, stage, err, err_cal, wet.sum() * cell_km2), flush=True)
    rep["steady"] = steady
    rep["passed"] = all(abs(s["difference_m"]) <= STAGE_TOL_M and s["floodplain_wet_km2"] <= WET_MAX_KM2 for s in steady)
    with open(os.path.join(ROOT, "data", "processed", "flood_run2_terrain.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print("CHECK 3", "PASSED" if rep["passed"] else "FAILED (stop: the design needs revising)")


if __name__ == "__main__":
    main()
