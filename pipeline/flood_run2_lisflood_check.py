"""Pre-run check 2 of flood run 2 (docs/model_design_flood_run2.md): LISFLOOD-FP 8.2's velocity
output and restart, on run 1's synthetic smoke channel. No observed flood and no radar image.

The synthetic case is run 1's (pipeline/flood_lisflood_smoke.py, imported, not changed): a 3 km x 1 km
valley on 20 m cells, an 11 m channel meandering as a sine wave, 2.11 m deep, its bed falling 1 in
2,700 along the curve; free outflow east. The channel roughness is run 2's (n = 0.020). Every run asks
for `voutput` (floodplain velocity), `SGCvoutput` (subgrid channel velocity), `qoutput` (discharge) and
`hazard` (without which this build writes the velocity grids as zeros).

  A. Channel only (floodplain 5 m above the banks), 15 m3/s, 24 hours. Records which files are
     written and what they hold. The channel velocity is taken by the design's stated rule if the
     model's channel velocity grid is empty: channel discharge (.Qcx/.Qcy, on cell faces) / (11 m x
     the cell's depth). Passes if, over the middle half of the channel, the median channel discharge
     is within 20% of 15 m3/s, so the velocity is within 20% of Q / (width x depth).
  C. Floodplain at bank level, 40 m3/s (the channel overtops), 6 hours. Passes if the floodplain
     velocity grid (.Vx/.Vy, on faces) is written and agrees with the floodplain discharge: on faces
     with flow, the median of |Vx| x face depth x 20 m / |Qx| is within 20% of 1.
  B. `startfile`: a run started from A's final depths for 1 hour. Passes if its first output (t = 0)
     holds the channel depths it was given within 1 cm in every channel cell but the inflow cell (where
     the inflow is added at t = 0, as in A's own first output), and the floodplain is dry.

Usage: python pipeline/flood_run2_lisflood_check.py  (needs Docker and atibaia/lisflood-fp:8.2).
Writes models/flood_run2/lisflood_check/ (not committed) and data/processed/flood_run2_lisflood_check.json.
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flood_lisflood_smoke as sm  # noqa: E402  (run 1's synthetic channel: geometry helpers only)

ROOT = sm.ROOT
IMAGE = sm.IMAGE
OUT = os.path.join(ROOT, "models", "flood_run2", "lisflood_check")
N_RUN2 = 0.020
# `hazard` too: this build computes the velocity grids only in hazard mode (without it .Vx/.Vy are written
# as zeros, as a first run of this check found)
OUTPUTS = "voutput\nSGCvoutput\nqoutput\nhazard\n"


def read_asc(path):
    with open(path) as f:
        for _ in range(6):
            f.readline()
        a = np.loadtxt(f)
    return np.where(a <= -9999, np.nan, a)


def build(out, above, q):
    """Run 1's smoke geometry with the floodplain `above` m over the banks and `q` m3/s in."""
    os.makedirs(out, exist_ok=True)
    path = sm.channel_path()
    top = 100.0
    bank = {(c, r): top - sm.SLOPE * s for c, r, s in path}
    width = [[0.0] * sm.NC for _ in range(sm.NR)]
    bankg = [[-9999.0] * sm.NC for _ in range(sm.NR)]
    bedg = [[-9999.0] * sm.NC for _ in range(sm.NR)]
    dem = [[top + above - sm.SLOPE * c * sm.DX * 1.5 for c in range(sm.NC)] for _ in range(sm.NR)]
    for (c, r), b in bank.items():
        width[r][c], bankg[r][c], bedg[r][c] = sm.WIDTH, b, b - sm.DEPTH
        dem[r][c] = b + above
    for name, g in (("dem", dem), ("width", width), ("bank", bankg), ("bed", bedg)):
        sm.asc(os.path.join(out, name + ".asc"), g)
    c0, r0, _ = path[0]
    with open(os.path.join(out, "check.bci"), "w") as f:  # QFIX is per unit width (m2/s)
        f.write("E 0 999999 FREE %.6f\nP %.1f %.1f QFIX %.5f\n" % (sm.SLOPE, (c0 + 0.5) * sm.DX, (sm.NR - r0 - 0.5) * sm.DX, q / sm.DX))
    return path


def par(out, hours, saveint, extra=""):
    with open(os.path.join(out, "check.par"), "w") as f:
        f.write("DEMfile dem.asc\nresroot res\ndirroot results\nsim_time %d\ninitial_tstep 1.0\nmassint 3600\n"
                "saveint %d\nfpfric 0.04\nbcifile check.bci\nacceleration\nSGCn %.3f\nSGCwidth width.asc\n"
                "SGCbank bank.asc\nSGCbed bed.asc\nelevoff\n%s" % (hours * 3600, saveint, N_RUN2, extra))
    cmd = ["docker", "run", "--rm", "-v", out.replace("\\", "/") + ":/data", IMAGE, "check.par"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
    if r.returncode != 0:
        sys.exit("LISFLOOD-FP failed in %s: %s" % (out, (r.stderr or r.stdout)[-800:]))


def grids(out, stem):
    res = {}
    for p in glob.glob(os.path.join(out, "results", stem + ".*")):
        ext = p.rsplit(".", 1)[1]
        try:
            res[ext] = read_asc(p)
        except ValueError:
            pass
    return res


def summary(g):
    return {k: {"rows_cols": list(v.shape), "nonzero": int((np.abs(np.nan_to_num(v)) > 1e-6).sum()),
                "abs_max": round(float(np.nanmax(np.abs(v))), 3)} for k, v in sorted(g.items())}


def channel_speed(g, path):
    """Per channel cell: mean |channel discharge| over its faces on the path / (11 m x depth)."""
    on = {(c, r) for c, r, _ in path}
    out = []
    for c, r, _ in path:
        qs = []
        if (c - 1, r) in on or (c + 1, r) in on:
            qs += [abs(g["Qcx"][r, c]) if (c - 1, r) in on else None, abs(g["Qcx"][r, c + 1]) if (c + 1, r) in on else None]
        if (c, r - 1) in on or (c, r + 1) in on:
            qs += [abs(g["Qcy"][r, c]) if (c, r - 1) in on else None, abs(g["Qcy"][r + 1, c]) if (c, r + 1) in on else None]
        qs = [q for q in qs if q is not None and np.isfinite(q)]
        d = g["wd"][r, c]
        out.append((float(np.mean(qs)) if qs else np.nan, float(d)))
    return out


def main():
    res = {"design": "docs/model_design_flood_run2.md", "check": "pre-run check 2", "n_channel": N_RUN2,
           "case": "run 1's synthetic smoke channel (flood_lisflood_smoke.py)", "outputs_asked": OUTPUTS.split()}

    # ---- A: channel only
    a = os.path.join(OUT, "A_channel_only")
    path = build(a, 5.0, sm.Q)
    par(a, 24, 3600, OUTPUTS)
    g = grids(a, "res-0024")
    res["A_grids"] = summary(g)
    mid = channel_speed(g, path)[len(path) // 4: 3 * len(path) // 4]
    q_med = float(np.nanmedian([q for q, _ in mid]))
    d_med = float(np.nanmedian([d for _, d in mid]))
    v_rule = float(np.nanmedian([q / (sm.WIDTH * d) for q, d in mid]))
    res["A_channel_velocity_grid_empty"] = res["A_grids"].get("SGCVx", {}).get("nonzero", 0) == 0
    res["A_middle_half"] = {"cells": len(mid), "median_channel_discharge_m3s": round(q_med, 3), "median_depth_m": round(d_med, 3),
                            "median_velocity_by_rule_ms": round(v_rule, 3), "Q_over_w_d_ms": round(sm.Q / (sm.WIDTH * d_med), 3)}
    res["A_passed"] = bool(abs(q_med - sm.Q) <= 0.2 * sm.Q)

    # ---- C: floodplain flow
    cdir = os.path.join(OUT, "C_floodplain")
    build(cdir, 0.0, 40.0)
    par(cdir, 6, 3600, OUTPUTS)
    gc = grids(cdir, "res-0006")
    res["C_grids"] = summary(gc)
    # x faces: depth on a face = mean of the floodplain depths either side
    fp = np.nan_to_num(gc["wdfp"])
    hf = np.zeros_like(gc["Vx"])
    hf[:, 1:-1] = (fp[:, :-1] + fp[:, 1:]) / 2
    sel = (np.abs(np.nan_to_num(gc["Qx"])) > 0.05) & (hf > 0.02) & (np.abs(np.nan_to_num(gc["Vx"])) > 0)
    ratio = np.abs(gc["Vx"][sel]) * hf[sel] * sm.DX / np.abs(gc["Qx"][sel])
    res["C_floodplain_faces_checked"] = int(sel.sum())
    res["C_median_V_h_dx_over_Q"] = round(float(np.median(ratio)), 3) if sel.any() else None
    res["C_passed"] = bool(sel.sum() >= 100 and abs(np.median(ratio) - 1) <= 0.2)

    # ---- B: restart from A's final depths
    b = os.path.join(OUT, "B_startfile")
    build(b, 5.0, sm.Q)
    with open(os.path.join(a, "results", "res-0024.wd")) as src, open(os.path.join(b, "start.wd"), "w") as dst:
        dst.write(src.read())
    par(b, 1, 600, "startfile start.wd\n")
    w0 = read_asc(os.path.join(b, "results", "res-0000.wd"))
    wa = g["wd"]
    diffs = [abs(float(w0[r, c]) - float(wa[r, c])) for c, r, _ in path]
    chan = np.zeros(wa.shape, bool)
    for c, r, _ in path:
        chan[r, c] = True
    res["B_channel_cells"] = len(path)
    res["B_inflow_cell_diff_m"] = round(diffs[0], 4)
    res["B_other_cells_max_diff_m"] = round(max(diffs[1:]), 4)
    res["B_floodplain_max_depth_m"] = round(float(np.nan_to_num(w0[~chan]).max()), 4)
    res["B_passed"] = bool(max(diffs[1:]) <= 0.01 and float(np.nan_to_num(w0[~chan]).max()) <= 0.001)

    res["passed"] = res["A_passed"] and res["C_passed"] and res["B_passed"]
    with open(os.path.join(ROOT, "data", "processed", "flood_run2_lisflood_check.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if not k.endswith("_grids")}, indent=1))
    print("CHECK 2", "PASSED" if res["passed"] else "FAILED")


if __name__ == "__main__":
    main()
