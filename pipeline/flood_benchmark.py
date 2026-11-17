"""Scoring mask and terrain-only benchmark for flood run 1.

docs/model_design_flood_run1.md, "Observed flood maps" (scoring mask) and
"The test" (terrain-only benchmark). Terrain, land cover and gauge records
only: no radar image and no model output is used, and both products are made
before any radar map exists. Run with the atibaia-sfincs environment.

Scoring grid (implementation detail): EPSG:32723 (WGS84 / UTM 23S), 10 m
cells on multiples of 10 m, the grid of Planetary Computer's sentinel-1-rtc
scenes (324 of the 330 orbit-53 scenes in the catalogue entries; the others
are resampled by nearest neighbour when the radar maps are made).

Scoring mask (design): inside the model domain, excluding the river channel
(the OSM line plus 15 m), built-up land (WorldCover 50), building footprints
plus 20 m, tree cover (WorldCover 10) and slopes over 10 degrees on ANADEM.

Benchmark (design): a cell is wet if its height above the river is no more
than (stage at the pass - 3.01 m) + H, where H is that height at the bank
cells at 3E-063. Height above the river is the HAND raster made by
pipeline/flood_build_model.py (ANADEM; drainage = the OSM line of the Rio
Atibaia, since the window cannot reach the 1,000 km2 threshold). The bank
cells are those of the bank rule: 35.5 m either side of the line (half the
11 m width plus 30 m), the lower of the two.

Outputs: data/processed/flood_run1_scoring_mask.tif, flood_run1_benchmark.tif
(one band per scored pass, 1 = wet), flood_run1_benchmark.json.

Usage: python pipeline/flood_benchmark.py
"""
import json
import math
import os
import sys

import geopandas as gpd
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio import features
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from shapely.ops import transform as shp_transform

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flood_build_model as fb  # noqa: E402

ROOT, RAW, PROC = fb.ROOT, fb.RAW, fb.PROC
TERR = os.path.join(ROOT, "models", "flood_run1", "terrain")
EPSG, RES = 32723, 10.0
OVERFLOW_M, BANK_OFFSET = 3.01, 11.0 / 2 + 30.0
CHANNEL_BUFFER, BUILDING_BUFFER, MAX_SLOPE = 15.0, 20.0, 10.0


def main():
    to_s = Transformer.from_crs(fb.EPSG, EPSG, always_xy=True)
    dom = gpd.read_file(os.path.join(TERR, "domain.gpkg")).to_crs(EPSG).geometry.iloc[0]
    minx, miny, maxx, maxy = dom.bounds
    x0, y0 = math.floor(minx / RES) * RES, math.floor(miny / RES) * RES
    x1, y1 = math.ceil(maxx / RES) * RES, math.ceil(maxy / RES) * RES
    W, H = int(round((x1 - x0) / RES)), int(round((y1 - y0) / RES))
    tr = from_origin(x0, y1, RES, RES)
    crs = f"EPSG:{EPSG}"
    inside = features.rasterize([(dom, 1)], out_shape=(H, W), transform=tr, dtype="uint8").astype(bool)

    def warp(src_arr, src_tr, src_crs, method, src_nodata, dtype="float32", dst_nodata=np.nan):
        out = np.full((H, W), dst_nodata, dtype=dtype)
        reproject(src_arr, out, src_transform=src_tr, src_crs=src_crs, dst_transform=tr, dst_crs=crs,
                  resampling=method, src_nodata=src_nodata, dst_nodata=dst_nodata)
        return out

    hsrc = rasterio.open(os.path.join(TERR, "hand_anadem.tif"))
    hand30 = hsrc.read(1)
    hand = warp(hand30, hsrc.transform, hsrc.crs, Resampling.bilinear, -9999.0)
    meta = json.load(open(os.path.join(RAW, "dem", "anadem_window.json"), encoding="utf-8"))
    bb = meta["bbox"]
    z = np.fromfile(os.path.join(RAW, "dem", "anadem_window.f32"), dtype="<f4").reshape(meta["height"], meta["width"])
    ztr = from_origin(bb["west"], bb["north"], (bb["east"] - bb["west"]) / meta["width"], (bb["north"] - bb["south"]) / meta["height"])
    dem = warp(z.astype("float32"), ztr, "EPSG:4326", Resampling.bilinear, -9999.0)
    gy, gx = np.gradient(dem, RES)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    wm = json.load(open(os.path.join(RAW, "worldcover", "worldcover_flood_run1.json"), encoding="utf-8"))
    wc = np.fromfile(os.path.join(RAW, "worldcover", "worldcover_flood_run1.u8"), dtype="u1").reshape(wm["height"], wm["width"])
    cls = warp(wc, from_origin(wm["west"], wm["north"], wm["pixel_deg"], wm["pixel_deg"]), "EPSG:4326",
               Resampling.nearest, 0, dtype="uint8", dst_nodata=0)

    line_utm, _ = fb.river_line_utm()
    line_s = shp_transform(lambda x, y, z=None: to_s.transform(x, y), line_utm)
    chan = features.rasterize([(line_s.buffer(CHANNEL_BUFFER), 1)], out_shape=(H, W), transform=tr,
                              all_touched=True, dtype="uint8").astype(bool)
    blds = gpd.read_file(os.path.join(TERR, "buildings.gpkg")).to_crs(EPSG).geometry.buffer(BUILDING_BUFFER)
    bld = features.rasterize([(g, 1) for g in blds], out_shape=(H, W), transform=tr, all_touched=True,
                             dtype="uint8").astype(bool)
    built, tree, steep = cls == 50, cls == 10, slope > MAX_SLOPE
    scoring = inside & ~chan & ~bld & ~built & ~tree & ~steep
    excluded = {k: int((inside & v).sum()) for k, v in
                (("channel", chan), ("buildings_20m", bld), ("built_up", built), ("tree_cover", tree), ("slope_over_10", steep))}

    # H: height above the river at the bank cells beside 3E-063 (on the 30 m raster, as the bank rule samples ANADEM)
    s_g = line_utm.project(fb.utm_point(*fb.GAUGE))
    a, b = line_utm.interpolate(s_g - 20), line_utm.interpolate(s_g + 20)
    tx, ty = b.x - a.x, b.y - a.y
    nrm = math.hypot(tx, ty)
    nx, ny = -ty / nrm, tx / nrm
    p = line_utm.interpolate(s_g)
    inv = ~hsrc.transform
    side = []
    for sgn in (1, -1):
        lon, lat = fb.TO_LL.transform(p.x + sgn * BANK_OFFSET * nx, p.y + sgn * BANK_OFFSET * ny)
        cc, rr = inv * (lon, lat)
        side.append(float(hand30[int(rr), int(cc)]))
    Hb = min(side)

    passes = [q for q in json.load(open(os.path.join(PROC, "flood_run1_passes.json"), encoding="utf-8"))["passes"] if q["scored"]]
    bands, rows = [], []
    for q in passes:
        stage = q["stage_cm"] / 100.0
        thr = stage - OVERFLOW_M + Hb
        wet = inside & np.isfinite(hand) & (hand <= thr)
        bands.append(wet.astype("uint8"))
        rows.append({"pass": q["pass"], "stage_m": round(stage, 3), "threshold_m": round(thr, 3),
                     "wet_km2_domain": round(wet.sum() * RES * RES / 1e6, 3),
                     "wet_km2_scored": round((wet & scoring).sum() * RES * RES / 1e6, 3)})

    prof = {"driver": "GTiff", "width": W, "height": H, "crs": crs, "transform": tr, "compress": "deflate", "dtype": "uint8"}
    with rasterio.open(os.path.join(PROC, "flood_run1_scoring_mask.tif"), "w", count=1, **prof) as f:
        f.write(scoring.astype("uint8"), 1)
        f.set_band_description(1, "1 = scored (open ground inside the domain)")
    with rasterio.open(os.path.join(PROC, "flood_run1_benchmark.tif"), "w", count=len(bands), **prof) as f:
        for k, (bnd, q) in enumerate(zip(bands, passes), start=1):
            f.write(bnd, k)
            f.set_band_description(k, "benchmark wet, pass %s" % q["pass"])
    summary = {"made": "before any radar map or model output existed", "grid": {"epsg": EPSG, "res_m": RES, "x0": x0, "y1": y1,
               "width": W, "height": H}, "H_bank_m": round(Hb, 3), "H_both_banks_m": [round(v, 3) for v in side],
               "domain_km2": round(inside.sum() * RES * RES / 1e6, 3), "scored_km2": round(scoring.sum() * RES * RES / 1e6, 3),
               "excluded_km2_by_rule": {k: round(v * RES * RES / 1e6, 3) for k, v in excluded.items()}, "passes": rows}
    json.dump(summary, open(os.path.join(PROC, "flood_run1_benchmark.json"), "w"), indent=1)
    print("grid %d x %d at 10 m (EPSG:%d); domain %.2f km2, scored %.2f km2; excluded (overlapping) %s"
          % (W, H, EPSG, summary["domain_km2"], summary["scored_km2"], summary["excluded_km2_by_rule"]))
    print("H (bank cells beside 3E-063) = %.2f m (sides %s)" % (Hb, summary["H_both_banks_m"]))
    for r in rows:
        print("  %s  stage %.2f m  threshold %.2f m  benchmark wet %.3f km2 (%.3f km2 on scored ground)"
              % (r["pass"], r["stage_m"], r["threshold_m"], r["wet_km2_domain"], r["wet_km2_scored"]))


if __name__ == "__main__":
    main()
