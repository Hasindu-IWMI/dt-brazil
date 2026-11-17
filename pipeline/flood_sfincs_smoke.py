"""Smoke test of the SFINCS engine for flood run 1 (part of pre-run check 5).

Not the design's domain test: that needs the channel widths of check 2. This
only shows that the pinned official engine runs on this machine and that a
water-level boundary holds a steady level, on a synthetic case:

  a straight valley 2 km long and 300 m wide on 20 m cells; a channel 60 m
  wide and 2 m deep along its axis, falling 1 in 2,500 (about the slope of the
  Atibaia through the town reach); floodplain 2 m above the channel bed;
  15 m3/s entering at the upstream end; a fixed water level 1.2 m above the
  bed at the downstream end; Manning n 0.04; 12 hours.

Pass: at a point half-way down, the water level changes by less than 1 cm
over the last 2 hours, and the discharge through a cross-section there is
within 5% of 15 m3/s.

Inputs are written in SFINCS's ASCII format (inputformat = asc), so no
HydroMT is involved. Run with the atibaia-sfincs environment (envs/flood-sfincs.yml),
which has netCDF4 to read the output:

  conda run -n atibaia-sfincs python pipeline/flood_sfincs_smoke.py

The model folder is models/smoke_sfincs/ (not committed).
"""
import os
import subprocess
import sys

import netCDF4
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = "deltares/sfincs-cpu:sfincs-v2.5.0-Hautacam"
OUT = os.path.join(ROOT, "models", "smoke_sfincs")
DX, M, N = 20.0, 100, 15            # cells along and across the valley
SLOPE, Q, DEPTH_BC = 1 / 2500.0, 15.0, 1.2


def write_inputs():
    os.makedirs(OUT, exist_ok=True)
    x = (np.arange(M) + 0.5) * DX
    bed = 10.0 - SLOPE * x                              # channel bed along the valley
    dep = np.tile(bed + 2.0, (N, 1))                    # floodplain 2 m above the bed
    dep[6:9, :] = bed                                   # channel: 3 cells (60 m) in the middle
    msk = np.ones((N, M), dtype=int)
    msk[:, -1] = 2                                      # downstream column: water-level boundary
    np.savetxt(os.path.join(OUT, "sfincs.dep"), dep, fmt="%.4f")
    np.savetxt(os.path.join(OUT, "sfincs.msk"), msk, fmt="%d")
    yc = 7.5 * DX
    level = bed[-1] + DEPTH_BC
    with open(os.path.join(OUT, "sfincs.bnd"), "w") as f:
        f.write("%.1f %.1f\n" % (x[-1], yc))
    with open(os.path.join(OUT, "sfincs.bzs"), "w") as f:
        f.write("0 %.4f\n43200 %.4f\n" % (level, level))
    with open(os.path.join(OUT, "sfincs.src"), "w") as f:
        f.write("%.1f %.1f\n" % (x[0], yc))
    with open(os.path.join(OUT, "sfincs.dis"), "w") as f:
        f.write("0 %.3f\n43200 %.3f\n" % (Q, Q))
    with open(os.path.join(OUT, "sfincs.obs"), "w") as f:
        f.write("%.1f %.1f\n" % (x[M // 2], yc))
    # cross-section across the valley, half-way (tekal polyline). It lies on a cell FACE: a line through
    # cell centres touches the faces on both sides and SFINCS then counts the flow twice (first run: 30 m3/s).
    xf = x[M // 2] - DX / 2
    with open(os.path.join(OUT, "sfincs.crs"), "w") as f:
        f.write("mid\n2 2\n%.1f %.1f\n%.1f %.1f\n" % (xf, 1.0, xf, N * DX - 1.0))
    inp = {"mmax": M, "nmax": N, "dx": DX, "dy": DX, "x0": 0, "y0": 0, "rotation": 0,
           "tref": "20000101 000000", "tstart": "20000101 000000", "tstop": "20000101 120000",
           "dtmapout": 3600, "dthisout": 600, "alpha": 0.5, "manning": 0.04, "huthresh": 0.01,
           "zsini": level, "inputformat": "asc", "outputformat": "net",
           "depfile": "sfincs.dep", "mskfile": "sfincs.msk", "bndfile": "sfincs.bnd", "bzsfile": "sfincs.bzs",
           "srcfile": "sfincs.src", "disfile": "sfincs.dis", "obsfile": "sfincs.obs", "crsfile": "sfincs.crs"}
    with open(os.path.join(OUT, "sfincs.inp"), "w") as f:
        for k, v in inp.items():
            f.write("%-12s = %s\n" % (k, v))


def main():
    write_inputs()
    cmd = ["docker", "run", "--rm", "-v", OUT.replace("\\", "/") + ":/data", IMAGE]
    print("running:", " ".join(cmd), flush=True)
    run = subprocess.run(cmd, capture_output=True, text=True)
    with open(os.path.join(OUT, "docker_run.log"), "w", encoding="utf-8") as f:
        f.write(run.stdout + "\n--- stderr ---\n" + run.stderr)
    print(run.stdout[-1500:])
    if run.returncode != 0:
        print(run.stderr[-1500:])
        sys.exit("SFINCS exited with %d" % run.returncode)
    his = netCDF4.Dataset(os.path.join(OUT, "sfincs_his.nc"))
    t = np.asarray(his.variables["time"][:], dtype=float)
    zs = np.asarray(his.variables["point_zs"][:]).reshape(len(t), -1)[:, 0]
    qcrs = None
    for name in ("crosssection_discharge", "cross_section_discharge", "crs_discharge"):
        if name in his.variables:
            qcrs = np.asarray(his.variables[name][:]).reshape(len(t), -1)[:, 0]
            break
    last = t >= t[-1] - 7200
    dz = float(zs[last].max() - zs[last].min())
    print("time steps in his:", len(t), "| level at the mid point, last 2 h: %.3f to %.3f m (change %.1f cm)"
          % (zs[last].min(), zs[last].max(), 100 * dz))
    ok = dz < 0.01
    if qcrs is not None:
        qend = float(np.mean(np.abs(qcrs[last])))
        print("discharge through the mid cross-section, last 2 h: %.2f m3/s (inflow %.1f)" % (qend, Q))
        ok = ok and abs(qend - Q) / Q < 0.05
    else:
        print("no cross-section discharge in the output; variables:", sorted(his.variables))
        ok = False
    print("SMOKE TEST", "PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
