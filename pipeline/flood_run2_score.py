"""Flood run 2: test B and the verdict file (docs/model_design_flood_run2.md: "Test B", "Acceptance",
"Velocities, the verdict file and the viewer").

The data gate failed (pre-run check 6), so there is no test A and run 2 is not accepted. The design:
"Test B is still run and reported, as information."

Test B, as fixed in the design:
  - the 13 morning passes scored in run 1, simulated by the event rules (pipeline/flood_run2_build.py);
  - deep water: modelled water at least 0.5 m deep on the run 2 scoring mask, at the hourly output
    nearest the pass;
  - passes if the median deep-water area is at most 0.10 km2 and no more than 2 of the 13 passes exceed
    0.20 km2;
  - reported: the area wet over 10 cm, and the CSI against run 1's committed morning maps.

Implementation: the modelled depth over the ground is LISFLOOD-FP's .wdfp (the same as .wd off the
channel; in a channel cell, the depth over the bank). It is taken from the 20 m model grid
(EPSG:31983) onto the 10 m scoring grid (EPSG:32723) by nearest neighbour. The run 2 scoring mask is
run 1's mask less mapped permanent water, exactly as check 6 made it (pipeline/flood_sm_maps.py).

Writes data/processed/flood_run2_test_b.json, docs/flood_run2_test_b.png and, once,
data/processed/flood_run2_verdict.json. The verdict is never overwritten: a second run compares its
result with the verdict and stops if they differ. The verdict's sha256 is stored in the test B file.

Usage (atibaia-sfincs environment): python pipeline/flood_run2_score.py
"""
import datetime as dt
import hashlib
import json
import os
import statistics
import sys

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c  # noqa: E402
import flood_sm_maps as sm  # noqa: E402  (the scoring grid and the permanent-water rule of check 6)

ROOT = c.ROOT
EVENTS_JSON = os.path.join(c.PROCESSED, "flood_run2_events_morning.json")
OBS_RUN1 = os.path.join(c.PROCESSED, "flood_run1_observed.tif")
GATE_JSON = os.path.join(c.PROCESSED, "flood_run2_observed.json")
OUT_JSON = os.path.join(c.PROCESSED, "flood_run2_test_b.json")
VERDICT = os.path.join(c.PROCESSED, "flood_run2_verdict.json")
FIG = os.path.join(ROOT, "docs", "flood_run2_test_b.png")
MODEL_EPSG = 31983
DEEP_M, WET_M = 0.50, 0.10
MEDIAN_MAX_KM2, BIG_KM2, BIG_MAX = 0.10, 0.20, 2
CELL_KM2 = 100 / 1e6


def read_asc(path):
    with open(path) as f:
        head = {}
        for _ in range(6):
            k, v = f.readline().split()
            head[k.lower()] = float(v)
    a = np.loadtxt(path, skiprows=6).astype("float32")
    tr = from_origin(head["xllcorner"], head["yllcorner"] + head["nrows"] * head["cellsize"], head["cellsize"], head["cellsize"])
    return a, tr


def to_grid(a, tr, grid):
    out = np.full((grid["height"], grid["width"]), np.nan, dtype="float32")
    reproject(a, out, src_transform=tr, src_crs="EPSG:%d" % MODEL_EPSG, dst_transform=grid["transform"], dst_crs=grid["crs"],
              resampling=Resampling.nearest, src_nodata=-9999.0, dst_nodata=np.nan)
    return out


def csi(model, obs, mask):
    a = int((model & obs & mask).sum())
    b = int((model & ~obs & mask).sum())
    d = int((~model & obs & mask).sum())
    return (round(a / (a + b + d), 4) if a + b + d else None), a, b, d


def figure(mask, depths, obs_bands, recs):
    """One panel per pass: modelled water 0.1-0.5 m light blue, at least 0.5 m dark blue, run 1's
    observed flooded pixels red, the scoring mask grey; labelled with the pass, stage and deep area."""
    from PIL import Image, ImageDraw
    from scipy import ndimage
    H, W = mask.shape
    s = 0.5
    h, w = int(H * s), int(W * s)
    cols, pad = 5, 22
    rows = (len(recs) + cols - 1) // cols
    img = Image.new("RGB", (cols * (w + 6) + 6, rows * (h + pad + 6) + 6), (250, 250, 248))
    edge = mask & ~ndimage.binary_erosion(mask)
    for k, (d, ob, r) in enumerate(zip(depths, obs_bands, recs)):
        rgb = np.full((H, W, 3), 236, "uint8")
        rgb[mask] = (214, 214, 208)
        rgb[edge] = (120, 120, 116)
        dd = np.nan_to_num(d)
        rgb[(dd > WET_M) & (dd < DEEP_M)] = (140, 190, 235)
        rgb[dd >= DEEP_M] = (20, 70, 170)
        rgb[ob & mask] = (215, 40, 40)
        tile = Image.fromarray(rgb).resize((w, h), Image.NEAREST)
        x0, y0 = 6 + (k % cols) * (w + 6), 6 + (k // cols) * (h + pad + 6)
        img.paste(tile, (x0, y0 + pad))
        dr = ImageDraw.Draw(img)
        dr.text((x0, y0), "%s  %d cm" % (r["pass"].replace("T", " "), round(r["stage_cm_at_pass_hour"])), fill=(20, 20, 20))
        dr.text((x0, y0 + 11), "deep %.3f km2, wet %.3f km2" % (r["deep_km2_on_mask"], r["wet_km2_on_mask"]), fill=(60, 60, 60))
    img.save(FIG)


def main():
    grid = sm.scoring_grid()
    perm = sm.permanent_water(grid)
    mask = grid["mask"] & ~perm
    gate_file = json.load(open(GATE_JSON, encoding="utf-8"))
    assert int(mask.sum()) == gate_file["scoring_mask_cells"], (int(mask.sum()), gate_file["scoring_mask_cells"])
    ev = json.load(open(EVENTS_JSON, encoding="utf-8"))
    with rasterio.open(OBS_RUN1) as src:
        assert src.crs == grid["crs"] and src.transform == grid["transform"]
        obs_by_pass = {d.rsplit("pass ", 1)[1]: src.read(k + 1) == 1 for k, d in enumerate(src.descriptions)}
    recs, depths, obs_bands = [], [], []
    for e in ev["events"]:
        res = os.path.join(ROOT, e["folder"], "stage2", "results")
        wdfp, tr = read_asc(os.path.join(res, "res-%04d.wdfp" % e["output_index"]))
        d = to_grid(wdfp, tr, grid)
        dd = np.nan_to_num(d)
        deep = (dd >= DEEP_M) & mask
        wet = (dd > WET_M) & mask
        ob = obs_by_pass[e["pass"]]
        score, a, b, dmiss = csi(dd > WET_M, ob, mask)
        recs.append({"pass": e["pass"], "output_hour_utc": e["output_hour_utc"], "stage_cm_at_pass_hour": e["stage_cm_at_pass_hour"],
                     "event_days": e["event_days"], "deep_km2_on_mask": round(int(deep.sum()) * CELL_KM2, 4),
                     "wet_km2_on_mask": round(int(wet.sum()) * CELL_KM2, 4),
                     "max_depth_m_on_mask": round(float(dd[mask].max()), 2),
                     "observed_run1_km2_on_mask": round(int((ob & mask).sum()) * CELL_KM2, 4),
                     "csi_wet_vs_run1_observed": score, "csi_counts": {"both": a, "model_only": b, "observed_only": dmiss},
                     "gauge_scale_m_modelled": e["stage2"]["gauge_scale_m_at_pass_modelled"],
                     "gauge_scale_m_observed": e["stage2"]["gauge_scale_m_at_pass_observed"]})
        depths.append(d)
        obs_bands.append(ob)
    deep = [r["deep_km2_on_mask"] for r in recs]
    med = statistics.median(deep)
    big = sum(x > BIG_KM2 for x in deep)
    test_b = {"passed": med <= MEDIAN_MAX_KM2 and big <= BIG_MAX, "passes": len(recs),
              "median_deep_km2": round(med, 4), "median_deep_km2_max": MEDIAN_MAX_KM2,
              "passes_over_0.20_km2": big, "passes_over_0.20_km2_max": BIG_MAX,
              "median_wet_over_10cm_km2": round(statistics.median(r["wet_km2_on_mask"] for r in recs), 4),
              "median_csi_vs_run1_observed": statistics.median([r["csi_wet_vs_run1_observed"] for r in recs
                                                                if r["csi_wet_vs_run1_observed"] is not None] or [None]),
              "role": "information: the data gate failed, so test B cannot make run 2 accepted"}
    gate = gate_file["gate"]
    test_a_passed = False  # there is no test A: the gate failed
    verdict = {"run": "flood run 2", "design": "docs/model_design_flood_run2.md",
               "passed": bool(gate["passed"] and test_a_passed and test_b["passed"]),
               "gate": gate, "test_a": None, "test_b": {k: v for k, v in test_b.items() if k != "role"},
               "tested_stage_cm": None,
               "notes": ["test_a is null: the data gate failed, so there is no extent test (design, 'Data gate').",
                         "tested_stage_cm is null: no extent was tested, so no stage range is tested.",
                         "Accepted only if the gate passes, test A passes and test B passes (design, 'Acceptance')."],
               "decided_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if os.path.exists(VERDICT):
        old = json.load(open(VERDICT, encoding="utf-8"))
        if old.get("passed") != verdict["passed"] or old.get("test_b") != verdict["test_b"]:
            sys.exit("The verdict file exists and differs from this result; it is never overwritten. Stopping.")
        print("verdict file exists and agrees; not rewritten")
    else:
        with open(VERDICT, "w", encoding="utf-8") as f:
            json.dump(verdict, f, indent=1)
        print("wrote", os.path.relpath(VERDICT, ROOT))
    sha = hashlib.sha256(open(VERDICT, "rb").read()).hexdigest()
    out = {"design": "docs/model_design_flood_run2.md", "test": "test B (known answer), reported as information",
           "built": dt.date.today().isoformat(), "rule": {"deep_m": DEEP_M, "wet_m": WET_M, "median_deep_km2_max": MEDIAN_MAX_KM2,
                                                         "big_km2": BIG_KM2, "big_passes_max": BIG_MAX,
                                                         "depth": ".wdfp at the output hour nearest the pass, nearest neighbour onto the scoring grid"},
           "scoring_mask_cells": int(mask.sum()), "test_b": test_b, "passes": recs,
           "verdict_file": os.path.relpath(VERDICT, ROOT).replace("\\", "/"), "verdict_sha256": sha}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    figure(mask, depths, obs_bands, recs)
    print("\n pass              stage  deep km2  wet km2  max m  gauge mod/obs  CSI vs run 1")
    for r in recs:
        print(" %-16s  %5.1f  %7.3f  %7.3f  %5.2f  %5.2f / %5.2f  %s" % (r["pass"], r["stage_cm_at_pass_hour"], r["deep_km2_on_mask"],
              r["wet_km2_on_mask"], r["max_depth_m_on_mask"], r["gauge_scale_m_modelled"], r["gauge_scale_m_observed"],
              r["csi_wet_vs_run1_observed"]))
    print(json.dumps(test_b))
    print("TEST B", "PASSED" if test_b["passed"] else "FAILED", "(information only); verdict passed =", verdict["passed"],
          "; verdict sha256", sha)


if __name__ == "__main__":
    main()
