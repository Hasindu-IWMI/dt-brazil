"""Modelled flood water (depth and velocity) for the viewer's water layer.

Converts LISFLOOD-FP grids of a flood run (ESRI ASCII, SIRGAS 2000 / UTM 23S,
EPSG:31983) to the viewer's geographic grid: depth in cm and velocity east and
north in cm/s, on a lon/lat grid at about the model's spacing (nearest cell).

Publishing rule (the flood runs' own rule): water is written to the viewer's
published data (web/public/data/flood_water.json) only for a run whose test
verdict file says it passed ({"passed": true}). Anything else can only be
written as a test file for checking the display in the development server
(web/dev-data/, which the build does not copy and git ignores); the viewer
shows that file only in development, with ?floodtest=1, under a TEST RENDER
banner.

Velocity: from the model's own velocity output where the run saved it (--vx,
--vy). A run that saved none (flood run 1's test runs) gets a DERIVED velocity,
for the display test only: Manning's equation on the modelled water-surface
slope, |v| = h^(2/3) S^(1/2) / n, pointing down the slope, capped at 4 m/s.

Usage (the display test, on flood run 1's steady 15 m3/s LISFLOOD-FP run):
  python flood_water_viewer.py --test --run models/flood_run1/lisflood/steady_15
      --depth results/res-0001.wd --label "steady 15 m3/s test flow"
Usage (a tested run): add --verdict <verdict.json> and --date YYYY-MM-DD per
frame instead of --test.
"""
import argparse
import base64
import json
import math
import os
import sys

import numpy as np
from pyproj import Transformer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

PUBLISHED = os.path.join(c.ROOT, "web", "public", "data", "flood_water.json")
TEST_OUT = os.path.join(c.ROOT, "web", "dev-data", "flood_water_test.json")
DEPTH_MIN_M = 0.05  # shallower cells are written dry
V_CAP = 4.0  # m/s, derived velocities only


def read_asc(path):
    """ESRI ASCII grid -> (array with NaN for nodata, header dict). Row 0 is north."""
    head = {}
    with open(path, encoding="ascii") as f:
        for _ in range(6):
            k, v = f.readline().split()
            head[k.lower()] = float(v)
        a = np.loadtxt(f, dtype=np.float64)
    a[a == head.get("nodata_value", -9999)] = np.nan
    return a, head


def publish_allowed(verdict_path):
    """True only if the run's verdict file exists and says it passed its test."""
    if not verdict_path or not os.path.exists(verdict_path):
        return False
    with open(verdict_path, encoding="utf-8") as f:
        return json.load(f).get("passed") is True


def derived_velocity(depth, wse, n, cell):
    """Manning's equation on the water-surface slope (central differences over wet cells)."""
    wet = depth >= DEPTH_MIN_M
    z = np.where(wet, wse, np.nan)
    # neighbours: a dry or missing neighbour takes the cell's own level (no slope that way)
    def shift(a, dr, dc):
        out = np.full_like(a, np.nan)
        r0, r1 = max(dr, 0), a.shape[0] + min(dr, 0)
        c0, c1 = max(dc, 0), a.shape[1] + min(dc, 0)
        out[r0:r1, c0:c1] = a[r0 - dr:r1 - dr, c0 - dc:c1 - dc]
        return np.where(np.isnan(out), a, out)
    east, west = shift(z, 0, -1), shift(z, 0, 1)
    north, south = shift(z, 1, 0), shift(z, -1, 0)  # row 0 is north
    gx = (east - west) / (2 * cell)  # dz/dx, x east
    gy = (north - south) / (2 * cell)  # dz/dy, y north
    s = np.hypot(gx, gy)
    speed = np.where(wet & (s > 0), np.minimum(V_CAP, depth ** (2 / 3) * np.sqrt(s) / n), 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        vx = np.where(s > 0, -gx / s * speed, 0.0)
        vy = np.where(s > 0, -gy / s * speed, 0.0)
    return np.nan_to_num(vx), np.nan_to_num(vy)


def to_lonlat_grid(depth, vx, vy, head):
    """Resample UTM 23S grids to a lon/lat grid (nearest cell); rotate velocity to true north."""
    nr, nc = depth.shape
    cs = head["cellsize"]
    x0, y0 = head["xllcorner"], head["yllcorner"]
    to_geo = Transformer.from_crs("EPSG:31983", "EPSG:4326", always_xy=True)
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:31983", always_xy=True)
    xs = np.array([x0, x0 + nc * cs, x0, x0 + nc * cs])
    ys = np.array([y0, y0, y0 + nr * cs, y0 + nr * cs])
    lon, lat = to_geo.transform(xs, ys)
    west, east, south, north = lon.min(), lon.max(), lat.min(), lat.max()
    lat0 = (south + north) / 2
    dlat = cs / 110570
    dlon = cs / (111320 * math.cos(math.radians(lat0)))
    W = int(round((east - west) / dlon))
    H = int(round((north - south) / dlat))
    glon = west + (np.arange(W) + 0.5) * (east - west) / W
    glat = north - (np.arange(H) + 0.5) * (north - south) / H
    LON, LAT = np.meshgrid(glon, glat)
    ux, uy = to_utm.transform(LON.ravel(), LAT.ravel())
    col = np.floor((np.asarray(ux) - x0) / cs).astype(int)
    row = np.floor((y0 + nr * cs - np.asarray(uy)) / cs).astype(int)
    inside = (col >= 0) & (col < nc) & (row >= 0) & (row < nr)
    d = np.zeros(W * H)
    u = np.zeros(W * H)
    v = np.zeros(W * H)
    d[inside] = depth[row[inside], col[inside]]
    u[inside] = vx[row[inside], col[inside]]
    v[inside] = vy[row[inside], col[inside]]
    d = np.nan_to_num(d)
    # grid north of UTM 23S vs true north: rotate the components by the meridian convergence
    xa, ya = to_utm.transform([lon.mean(), lon.mean()], [lat0, lat0 + 0.01])
    conv = math.atan2(xa[1] - xa[0], ya[1] - ya[0])  # angle of true north, east of grid north
    # true north is (sin g, cos g) and true east (cos g, -sin g) in grid axes
    ue = u * math.cos(conv) - v * math.sin(conv)
    vn = u * math.sin(conv) + v * math.cos(conv)
    dry = d < DEPTH_MIN_M
    d[dry] = 0
    ue[dry] = 0
    vn[dry] = 0
    grid = {"west": west, "east": east, "south": south, "north": north, "width": W, "height": H, "rows": "north first"}
    return grid, d.reshape(H, W), ue.reshape(H, W), vn.reshape(H, W)


def b64(a, dtype):
    return base64.b64encode(np.ascontiguousarray(a, dtype=dtype).tobytes()).decode("ascii")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", required=True, help="LISFLOOD-FP run folder (run.par, dem.asc, bed.asc)")
    ap.add_argument("--depth", required=True, nargs="+", help="depth grids (.wd), relative to --run")
    ap.add_argument("--vx", nargs="*", default=[], help="velocity grids, east (one per depth grid)")
    ap.add_argument("--vy", nargs="*", default=[], help="velocity grids, north")
    ap.add_argument("--date", nargs="*", default=[], help="the date of each depth grid (YYYY-MM-DD)")
    ap.add_argument("--label", default="", help="a label for the frames")
    ap.add_argument("--run-name", default="", help="the flood run, as the viewer should name it")
    ap.add_argument("--verdict", help="the run's test verdict file; publishing needs passed: true")
    ap.add_argument("--test", action="store_true", help="write the development test file only")
    a = ap.parse_args()
    run = os.path.join(c.ROOT, a.run) if not os.path.isabs(a.run) else a.run
    if not a.test and not publish_allowed(a.verdict):
        sys.exit("refused: this run has no verdict that says it passed its test; use --test for a display check")
    par = {}
    for line in open(os.path.join(run, "run.par"), encoding="ascii"):
        bits = line.split()
        if len(bits) >= 2:
            par[bits[0]] = bits[1]
    dem, head = read_asc(os.path.join(run, par.get("DEMfile", "dem.asc")))
    bed = read_asc(os.path.join(run, par["SGCbed"]))[0] if "SGCbed" in par else None
    width = read_asc(os.path.join(run, par["SGCwidth"]))[0] if "SGCwidth" in par else None
    n_fp = float(par.get("fpfric", 0.035))
    n_ch = float(par.get("SGCn", n_fp))
    derived = not a.vx
    frames = []
    for k, rel in enumerate(a.depth):
        wd, h2 = read_asc(os.path.join(run, rel))
        assert wd.shape == dem.shape and h2["cellsize"] == head["cellsize"], "depth grid does not match the DEM"
        wd = np.nan_to_num(wd)
        # sub-grid channel cells: those with a channel width; their depth is measured from the channel bed
        channel = (np.nan_to_num(width) > 0) if width is not None and bed is not None else np.zeros_like(wd, bool)
        wse = np.where(channel, np.nan_to_num(bed) + wd, dem + wd)
        if derived:
            vx, vy = derived_velocity(wd, wse, np.where(channel, n_ch, n_fp), head["cellsize"])
        else:
            vx = np.nan_to_num(read_asc(os.path.join(run, a.vx[k]))[0])
            vy = np.nan_to_num(read_asc(os.path.join(run, a.vy[k]))[0])
        grid, d, u, v = to_lonlat_grid(wd, vx, vy, head)
        frames.append({
            "date": a.date[k] if k < len(a.date) else None, "label": a.label,
            "depth_cm": b64(np.round(d * 100), "<u2"), "ve_cms": b64(np.round(u * 100), "<i2"), "vn_cms": b64(np.round(v * 100), "<i2"),
            "max_depth_m": round(float(d.max()), 2), "max_speed_ms": round(float(np.hypot(u, v).max()), 2),
            "wet_km2": round(float((d >= DEPTH_MIN_M).sum()) * head["cellsize"] ** 2 / 1e6, 3),
        })
    out = {
        "run": a.run_name or a.run.replace("\\", "/"),
        "accepted": not a.test,
        "status": ("tested: passed its test (" + os.path.relpath(a.verdict, c.ROOT).replace("\\", "/") + ")") if not a.test
        else "TEST RENDER: untested; for checking the display in development only, never published",
        "model": "LISFLOOD-FP", "source_crs": "EPSG:31983", "source_cell_m": head["cellsize"],
        "velocity": "derived: Manning's equation on the modelled water-surface slope (the run saved no velocities)" if derived
        else "the model's own velocity output",
        "depth_min_m": DEPTH_MIN_M, "grid": grid, "frames": frames,
    }
    path = TEST_OUT if a.test else PUBLISHED
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(f"wrote {os.path.relpath(path, c.ROOT)}: {grid['width']} x {grid['height']} cells, "
          + ", ".join(f"{fr['wet_km2']} km2 wet, max {fr['max_depth_m']} m, {fr['max_speed_ms']} m/s" for fr in frames))


if __name__ == "__main__":
    main()
