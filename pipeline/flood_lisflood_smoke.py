"""Smoke test of LISFLOOD-FP 8.2's subgrid channel for flood run 1 (pre-run check 5, repeated
for the new model).

SFINCS was set aside because, with only the channel open, it carried 15 m3/s in
an 11 m meandering channel at 5-9 m depth instead of about 2 m. This test asks
LISFLOOD-FP the same question on a synthetic case built like the Atibaia reach:

  a 3 km x 1 km valley on 20 m cells; a channel 11 m wide meandering as a sine
  wave (amplitude 150 m, wavelength 600 m: sharper than the real reach), its
  bed falling 1 in 2,700 along its true, curved length, 2.11 m below its banks;
  15 m3/s entering at the west end; free outflow at the east edge.
  Run A: floodplain 5 m above the banks (channel only).
  Run B: floodplain at bank level.

The channel is drawn as a 4-connected path of cells (LISFLOOD-FP exchanges
channel flow across cell faces, not corners).

Pass (run A): the water depth half-way along the channel, after 24 hours, is
within 25% of Manning's normal depth for an 11 m rectangular channel with
n = 0.035, using the bed slope the model actually sees (bed drop over the
length of the cell path). Run B is reported.

Usage: python pipeline/flood_lisflood_smoke.py   (needs Docker and the image
atibaia/lisflood-fp:8.2, see envs/lisflood-fp.Dockerfile). Writes
models/lisflood_smoke/ (not committed).
"""
import math
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = "atibaia/lisflood-fp:8.2"
DX, NC, NR = 20.0, 150, 50
WIDTH, DEPTH, SLOPE, Q, N_CH = 11.0, 2.11, 1 / 2700.0, 15.0, 0.035


def asc(path, grid, nodata=-9999):
    with open(path, "w") as f:
        f.write("ncols %d\nnrows %d\nxllcorner 0\nyllcorner 0\ncellsize %g\nNODATA_value %d\n" % (NC, NR, DX, nodata))
        for row in grid:
            f.write(" ".join("%.3f" % v for v in row) + "\n")


def channel_path():
    """Cells of the sine centreline as a 4-connected path, each with its distance along the true curve."""
    cells, s, prev_xy = [], 0.0, None
    x = 1.0
    while x < NC * DX - 1:
        y = 500.0 + 150.0 * math.sin(2 * math.pi * x / 600.0)
        if prev_xy is not None:
            s += math.hypot(x - prev_xy[0], y - prev_xy[1])
        prev_xy = (x, y)
        c, r = int(x // DX), NR - 1 - int(y // DX)
        if not cells or cells[-1][:2] != (c, r):
            if cells:
                pc, pr = cells[-1][:2]
                if pc != c and pr != r:  # diagonal step: insert the corner cell so the path stays 4-connected
                    cells.append((c, pr, s))
                    # walk vertically if more than one row was skipped
                while abs(cells[-1][1] - r) > 1:
                    cells.append((c, cells[-1][1] + (1 if r > cells[-1][1] else -1), s))
            cells.append((c, r, s))
        x += 0.5
    out, seen = [], set()
    for c, r, s in cells:
        if (c, r) not in seen:
            seen.add((c, r))
            out.append((c, r, s))
    return out


def run(case, floodplain_above_bank):
    out = os.path.join(ROOT, "models", "lisflood_smoke", case)
    os.makedirs(out, exist_ok=True)
    path = channel_path()
    top = 100.0
    bank = {(c, r): top - SLOPE * s for c, r, s in path}
    width = [[0.0] * NC for _ in range(NR)]
    bankg = [[-9999.0] * NC for _ in range(NR)]
    bedg = [[-9999.0] * NC for _ in range(NR)]
    dem = [[top + floodplain_above_bank] * NC for _ in range(NR)]
    for (c, r), b in bank.items():
        width[r][c], bankg[r][c], bedg[r][c] = WIDTH, b, b - DEPTH
        dem[r][c] = b + floodplain_above_bank
    # floodplain falls with the valley so it drains
    for r in range(NR):
        for c in range(NC):
            if (c, r) not in bank:
                dem[r][c] = top + floodplain_above_bank - SLOPE * c * DX * 1.5
    asc(os.path.join(out, "dem.asc"), dem)
    asc(os.path.join(out, "width.asc"), width)
    asc(os.path.join(out, "bank.asc"), bankg)
    asc(os.path.join(out, "bed.asc"), bedg)
    c0, r0, _ = path[0]
    mid = path[len(path) // 2]
    # QFIX/QVAR are per unit width (m2/s); LISFLOOD-FP multiplies by the cell size. (First run passed 15 and
    # got 300 m3/s, as the mass file showed.)
    with open(os.path.join(out, "smoke.bci"), "w") as f:
        f.write("E 0 999999 FREE %.6f\nP %.1f %.1f QFIX %.5f\n" % (SLOPE, (c0 + 0.5) * DX, (NR - r0 - 0.5) * DX, Q / DX))
    with open(os.path.join(out, "smoke.stage"), "w") as f:
        f.write("1\n%.1f %.1f\n" % ((mid[0] + 0.5) * DX, (NR - mid[1] - 0.5) * DX))
    with open(os.path.join(out, "smoke.par"), "w") as f:
        f.write("DEMfile dem.asc\nresroot res\ndirroot results\nsim_time 86400\ninitial_tstep 1.0\nmassint 3600\n"
                "saveint 86400\nfpfric 0.04\nbcifile smoke.bci\nstagefile smoke.stage\nacceleration\n"
                "SGCn %.3f\nSGCwidth width.asc\nSGCbank bank.asc\nSGCbed bed.asc\nelevoff\n" % N_CH)
    cmd = ["docker", "run", "--rm", "-v", out.replace("\\", "/") + ":/data", IMAGE, "smoke.par"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-1500:])
        sys.exit("LISFLOOD-FP exited with %d" % r.returncode)
    mass = [ln.split() for ln in open(os.path.join(out, "results", "res.mass")).read().splitlines()[1:] if ln.strip()]
    qin, qout = float(mass[-1][6]), float(mass[-1][8])
    if abs(qin - Q) > 0.01 * Q:
        sys.exit("inflow is %.3f m3/s, expected %.1f" % (qin, Q))
    lines = [ln.split() for ln in open(os.path.join(out, "results", "res.stage")).read().splitlines()]
    data = [ln for ln in lines if len(ln) >= 2 and ln[0].replace(".", "", 1).isdigit()]
    t_last, depth = float(data[-1][0]), float(data[-1][1])
    prev = [d for d in data if float(d[0]) <= t_last - 7200]
    d_prev = float(prev[-1][1]) if prev else float("nan")
    # slope the model sees: bank drop over the path length (cell-centre spacing)
    drop = bank[(path[0][0], path[0][1])] - bank[(path[-1][0], path[-1][1])]
    s_model = drop / ((len(path) - 1) * DX)
    lo, hi = 0.01, 10.0
    for _ in range(60):
        h = (lo + hi) / 2
        A, P = WIDTH * h, WIDTH + 2 * h
        q = A * (A / P) ** (2 / 3) * math.sqrt(s_model) / N_CH
        lo, hi = (h, hi) if q < Q else (lo, h)
    return {"case": case, "qin": qin, "qout": qout, "cells": len(path), "path_m": (len(path) - 1) * DX, "curve_m": path[-1][2],
            "slope_model": s_model, "depth": depth, "depth_2h_before": d_prev, "manning": h}


def main():
    res = [run("A_channel_only", 5.0), run("B_floodplain_at_bank", 0.0)]
    for r in res:
        print("%-22s Q in/out %.2f/%.2f m3/s; path %d cells (%.0f m; true curve %.0f m), slope seen 1 in %.0f; "
              "depth mid-channel %.2f m (2 h earlier %.2f); Manning normal depth %.2f m"
              % (r["case"], r["qin"], r["qout"], r["cells"], r["path_m"], r["curve_m"], 1 / r["slope_model"],
                 r["depth"], r["depth_2h_before"], r["manning"]))
    a = res[0]
    ok = abs(a["depth"] - a["manning"]) / a["manning"] <= 0.25 and abs(a["depth"] - a["depth_2h_before"]) < 0.01
    print("SMOKE TEST", "PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
