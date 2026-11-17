"""Observed flood maps from Sentinel-1 and the data gate, for flood run 1.

docs/model_design_flood_run1.md, "Observed flood maps, fixed before any model
run". The rule below is the design's, applied once to every scored pass. Uses
no model output (no modelled flood map exists when this runs). Run with the
atibaia-sfincs environment (rasterio reads the radar scenes; they use TIFF's
floating-point predictor, which pipeline/cogread.py does not decode).

Rule (design)
  Images: Planetary Computer sentinel-1-rtc (terrain-corrected gamma0, 10 m,
  CC BY 4.0), VV polarisation, in dB.
  Reference: per pixel, the median of the pass's dry references (same
  relative orbit, within 60 days, 3E-063 below 240 cm; listed in
  data/processed/flood_run1_passes.json; at least three).
  Flooded pixel: VV at the pass at least 3 dB below the reference AND below
  -15 dB.
  Scored only on the scoring mask (data/processed/flood_run1_scoring_mask.tif).
  A pass with fewer than 1,000 flooded pixels (0.1 km2) in the mask is
  reported, not scored.
  Data gate: across the scored passes, the flooded area in the mask must rise
  with the stage at the pass: Spearman correlation at least 0.5. Otherwise
  run 1 stops.

Grid: the scoring grid (EPSG:32723, 10 m). Scenes on the same 10 m lattice are
read pixel for pixel; others are resampled by nearest neighbour.

Provenance: each scene window read is logged in data/raw/manifest.jsonl with
the asset URL (without the access token), the window, and the SHA-256 of the
values read. The windows themselves are cached in models/flood_run1/radar/
(not committed).

Outputs: data/processed/flood_run1_observed.tif (one band per pass: 0 dry,
1 flooded, 255 no radar data; inside the domain), flood_run1_observed.json.

Usage: python pipeline/flood_radar_maps.py
"""
import concurrent.futures as cf
import gzip
import glob
import hashlib
import json
import os
import sys
import time
import urllib.request

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c  # noqa: E402

PROC, RAW = c.PROCESSED, c.RAW
CACHE = os.path.join(c.ROOT, "models", "flood_run1", "radar")
TOKEN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-rtc"
SOURCE = "Sentinel-1 RTC (Microsoft Planetary Computer, sentinel-1-rtc, CC BY 4.0), VV"
DROP_DB, MAX_DB, MIN_PIXELS, MIN_REFS, GATE_RHO = 3.0, -15.0, 1000, 3, 0.5
_token = {"value": None, "t": 0}

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "4")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "5")


def token():
    if _token["value"] is None or time.time() - _token["t"] > 1800:
        req = urllib.request.Request(TOKEN_URL, headers={"User-Agent": c.USER_AGENT})
        _token["value"] = json.load(urllib.request.urlopen(req, timeout=60))["token"]
        _token["t"] = time.time()
    return _token["value"]


def items_by_id():
    out = {}
    for fn in glob.glob(os.path.join(RAW, "s1", "s1rtc_*.json.gz")):
        for f in json.load(gzip.open(fn, "rt", encoding="utf-8"))["features"]:
            out[f["id"]] = f
    return out


def read_scene(item, grid):
    """VV in dB on the scoring grid (NaN where no data); cached."""
    path = os.path.join(CACHE, item["id"] + "_vv_db.npy")
    if os.path.exists(path):
        return np.load(path)
    href = item["assets"]["vv"]["href"]
    tr, W, H = grid["transform"], grid["width"], grid["height"]
    x0, y1 = tr.c, tr.f
    x1, y0 = x0 + W * tr.a, y1 + H * tr.e
    for attempt in range(4):
        try:
            with rasterio.open(href + "?" + token()) as src:
                win = from_bounds(x0 - 20, y0 - 20, x1 + 20, y1 + 20, src.transform).round_offsets().round_lengths()
                arr = src.read(1, window=win, boundless=True, fill_value=src.nodata if src.nodata is not None else -32768)
                wtr = src.window_transform(win)
                nod = src.nodata if src.nodata is not None else -32768
                crs = src.crs
            break
        except rasterio.errors.RasterioIOError:
            if attempt == 3:
                raise
            _token["value"] = None
            time.sleep(10 * (attempt + 1))
    lin = np.where((arr == nod) | ~np.isfinite(arr) | (arr <= 0), np.nan, arr).astype("float32")
    out = np.full((H, W), np.nan, dtype="float32")
    reproject(lin, out, src_transform=wtr, src_crs=crs, dst_transform=tr, dst_crs=crs,
              resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
    db = (10.0 * np.log10(out)).astype("float32")
    os.makedirs(CACHE, exist_ok=True)
    np.save(path, db)
    c.append_manifest({"source": SOURCE, "url": href, "file": None, "window": [x0, y0, x1, y1],
                       "grid": "EPSG:32723 10 m scoring grid", "sha256_values": hashlib.sha256(np.nan_to_num(db, nan=-999).tobytes()).hexdigest(),
                       "note": "radar window for flood run 1 (cached outside git)"})
    return db


def pass_mosaic(scenes, ids):
    """One pass from its slices: the first slice with data at each pixel (slices of a pass are adjacent frames)."""
    out = None
    for i in ids:
        a = scenes[i]
        out = a.copy() if out is None else np.where(np.isfinite(out), out, a)
    return out


def slices_of(items, item_id, seconds=120):
    """All catalogue items of the same orbit taken within `seconds` of the given one (the pass's slices)."""
    import datetime as dt
    p0 = items[item_id]["properties"]
    t0 = dt.datetime.fromisoformat(p0["datetime"][:19])
    return sorted(i for i, f in items.items()
                  if f["properties"].get("sat:relative_orbit") == p0.get("sat:relative_orbit")
                  and abs((dt.datetime.fromisoformat(f["properties"]["datetime"][:19]) - t0).total_seconds()) <= seconds)


def spearman(x, y):
    def ranks(v):
        order = np.argsort(v, kind="mergesort")
        r = np.empty(len(v))
        r[order] = np.arange(1, len(v) + 1)
        for val in np.unique(v):  # average ranks for ties
            m = v == val
            r[m] = r[m].mean()
        return r
    rx, ry = ranks(np.asarray(x, float)), ranks(np.asarray(y, float))
    return float(np.corrcoef(rx, ry)[0, 1])


def main():
    with rasterio.open(os.path.join(PROC, "flood_run1_scoring_mask.tif")) as m:
        mask = m.read(1).astype(bool)
        grid = {"transform": m.transform, "width": m.width, "height": m.height, "crs": m.crs}
    passes = [p for p in json.load(open(os.path.join(PROC, "flood_run1_passes.json"), encoding="utf-8"))["passes"] if p["scored"]]
    items = items_by_id()
    # A pass over Atibaia comes as two adjacent slices (frames). The first run used one slice per pass and
    # counted each slice of a reference date as a reference; a pass is now the mosaic of its slices, and
    # the references are counted by date (implementation fix, 17 November 2026; the rule is unchanged).
    pass_slices = {p["pass"]: slices_of(items, p["item"]) for p in passes}
    ref_groups = {}
    for p in passes:
        groups, seen = [], set()
        for r in p["references"]:
            if r["item"] in seen:
                continue
            g = slices_of(items, r["item"])
            seen.update(g)
            groups.append(g)
        ref_groups[p["pass"]] = groups
    need = sorted({i for v in pass_slices.values() for i in v} | {i for gs in ref_groups.values() for g in gs for i in g})
    print("scenes to read: %d (%d passes, %d references counted with repeats)"
          % (len(need), len(passes), sum(len(p["references"]) for p in passes)), flush=True)
    scenes = {}
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(read_scene, items[i], grid): i for i in need}
        for k, fu in enumerate(cf.as_completed(futs), 1):
            scenes[futs[fu]] = fu.result()
            if k % 10 == 0 or k == len(need):
                print("  read %d of %d" % (k, len(need)), flush=True)

    bands, rows = [], []
    for p in passes:
        vv = pass_mosaic(scenes, pass_slices[p["pass"]])
        refs = np.stack([pass_mosaic(scenes, g) for g in ref_groups[p["pass"]]])
        nref = np.sum(np.isfinite(refs), axis=0)
        ref = np.nanmedian(np.where(nref[None] >= MIN_REFS, refs, np.nan), axis=0)
        valid = np.isfinite(vv) & np.isfinite(ref) & (nref >= MIN_REFS)
        flooded = valid & (vv - ref <= -DROP_DB) & (vv < MAX_DB)
        band = np.where(valid, flooded.astype("uint8"), 255).astype("uint8")
        bands.append(band)
        n_mask = int((flooded & mask).sum())
        rows.append({"pass": p["pass"], "item": p["item"], "slices": pass_slices[p["pass"]], "stage_cm": p["stage_cm"],
                     "references": len(ref_groups[p["pass"]]),
                     "mask_pixels": int(mask.sum()), "mask_pixels_with_data": int((valid & mask).sum()),
                     "flooded_pixels_in_mask": n_mask, "flooded_km2_in_mask": round(n_mask * 100 / 1e6, 4),
                     "flooded_pixels_anywhere": int(flooded.sum()), "scored": n_mask >= MIN_PIXELS,
                     "median_vv_db_in_mask": round(float(np.nanmedian(vv[mask])), 2),
                     "median_ref_db_in_mask": round(float(np.nanmedian(ref[mask])), 2)})
    scored = [r for r in rows if r["scored"]]
    rho = spearman([r["stage_cm"] for r in scored], [r["flooded_pixels_in_mask"] for r in scored]) if len(scored) >= 3 else float("nan")
    gate = bool(np.isfinite(rho) and rho >= GATE_RHO)

    prof = {"driver": "GTiff", "width": grid["width"], "height": grid["height"], "crs": grid["crs"],
            "transform": grid["transform"], "compress": "deflate", "dtype": "uint8", "nodata": 255}
    with rasterio.open(os.path.join(PROC, "flood_run1_observed.tif"), "w", count=len(bands), **prof) as f:
        for k, (b, p) in enumerate(zip(bands, passes), 1):
            f.write(b, k)
            f.set_band_description(k, "observed flooded (Sentinel-1 rule), pass %s" % p["pass"])
    out = {"rule": {"drop_db": DROP_DB, "max_db": MAX_DB, "min_flooded_pixels": MIN_PIXELS, "min_references": MIN_REFS,
                    "gate_spearman_min": GATE_RHO},
           "made": "before any modelled flood map existed", "passes": rows, "scored_passes": len(scored),
           "spearman_stage_vs_flooded_area": None if not np.isfinite(rho) else round(rho, 3), "data_gate_passed": gate}
    json.dump(out, open(os.path.join(PROC, "flood_run1_observed.json"), "w"), indent=1)
    print("\n  pass               stage  refs  flooded px in mask  km2     data in mask  scored")
    for r in rows:
        print("  %s  %3d cm  %3d   %8d          %.3f   %5.1f%%       %s"
              % (r["pass"], r["stage_cm"], r["references"], r["flooded_pixels_in_mask"], r["flooded_km2_in_mask"],
                 100 * r["mask_pixels_with_data"] / r["mask_pixels"], "yes" if r["scored"] else "no (< 1,000 px)"))
    print("\n  scored passes: %d; Spearman (stage vs flooded area): %s; DATA GATE %s"
          % (len(scored), out["spearman_stage_vs_flooded_area"], "PASSED" if gate else "FAILED: run 1 stops"))


if __name__ == "__main__":
    main()
