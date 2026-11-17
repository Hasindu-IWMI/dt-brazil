"""River profile on ANADEM for flood run 1 (pre-run check 1 of docs/model_design_flood_run1.md).

Samples the bare-earth ANADEM window (fetch_anadem_window.py) and, for
comparison, the Copernicus GLO-30 surface model used by delineate.py, along
the OpenStreetMap line of the Rio Atibaia (web/public/data/vectors.json),
from 1.5 km upstream of SP Águas' gauge 3E-063 to ANA's station 62671200
above the Salto Grande plant. Every 30 m along the line it records:
  anadem_c     ANADEM on the line (bilinear)
  anadem_45    the lower of ANADEM 45 m either side of the line
  anadem_90    the lower of ANADEM 90 m either side
  glo30_c      GLO-30 (3 arc-seconds, a surface model) on the line
This is the terrain the flood model will stand on; no model is run. The bank
heights used by the design need the channel widths (pre-run check 2), so
they are not computed here.

Outputs: data/processed/flood_run1_profile.csv, docs/flood_run1_profile.svg,
and a short summary printed for the design addendum.

Usage: python flood_terrain.py
"""
import array
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

GAUGE = (-23.106111, -46.556389)      # 3E-063 (SIBH station list)
STATION = (-23.1058, -46.5958)        # 62671200 (SIBH station list)
UPSTREAM_M, STEP_M = 1500.0, 30.0
KX = 111320.0 * math.cos(math.radians(-23.1))  # metres per degree of longitude here
KY = 110574.0


def grid(path):
    meta = json.load(open(path + ".json", encoding="utf-8"))
    z = array.array("f")
    z.frombytes(open(path + ".f32", "rb").read())
    bb = meta["bbox"]
    W, H = meta["width"], meta["height"]
    dx, dy = (bb["east"] - bb["west"]) / W, (bb["north"] - bb["south"]) / H

    def at(lat, lon):  # bilinear on cell centres
        fx, fy = (lon - bb["west"]) / dx - 0.5, (bb["north"] - lat) / dy - 0.5
        x0, y0 = int(math.floor(fx)), int(math.floor(fy))
        if x0 < 0 or y0 < 0 or x0 + 1 >= W or y0 + 1 >= H:
            return None
        tx, ty = fx - x0, fy - y0
        v = [z[(y0 + j) * W + x0 + i] for j in (0, 1) for i in (0, 1)]
        return (v[0] * (1 - tx) + v[1] * tx) * (1 - ty) + (v[2] * (1 - tx) + v[3] * tx) * ty
    return at


def main():
    anadem = grid(os.path.join(c.RAW, "dem", "anadem_window"))
    glo30 = grid(os.path.join(c.RAW, "dem", "delineation"))
    vec = json.load(open(os.path.join(c.ROOT, "web", "public", "data", "vectors.json"), encoding="utf-8"))
    # the OSM segment of the Rio Atibaia that runs through the town reach
    seg = max((r for r in vec["rivers"] if (r.get("name") or "") == "Rio Atibaia"
               and min(p[0] for p in r["line"]) < STATION[1] + 0.01 and max(p[0] for p in r["line"]) > GAUGE[1] + 0.02),
              key=lambda r: len(r["line"]))
    pts = [(p[1], p[0]) for p in seg["line"]]
    if pts[0][1] < pts[-1][1]:  # the river flows west here: order from east (upstream) to west
        pts.reverse()
    cum = [0.0]
    for (a, b), (c2, d) in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.hypot((d - b) * KX, (c2 - a) * KY))

    def project(lat, lon):
        best = None
        for k in range(len(pts) - 1):
            (a, b), (c2, d) = pts[k], pts[k + 1]
            vx, vy = (d - b) * KX, (c2 - a) * KY
            wx, wy = (lon - b) * KX, (lat - a) * KY
            L2 = vx * vx + vy * vy
            t = max(0.0, min(1.0, (wx * vx + wy * vy) / L2)) if L2 else 0.0
            dist = math.hypot(wx - t * vx, wy - t * vy)
            if best is None or dist < best[0]:
                best = (dist, cum[k] + t * math.sqrt(L2))
        return best

    def point(s):  # position and unit normal at distance s along the line
        k = max(0, min(len(pts) - 2, next((i for i in range(len(cum) - 1) if cum[i + 1] >= s), len(cum) - 2)))
        (a, b), (c2, d) = pts[k], pts[k + 1]
        L = cum[k + 1] - cum[k] or 1.0
        t = (s - cum[k]) / L
        lat, lon = a + t * (c2 - a), b + t * (d - b)
        vx, vy = (d - b) * KX / L, (c2 - a) * KY / L
        return lat, lon, -vy, vx

    dg, sg = project(*GAUGE)
    ds, ss = project(*STATION)
    rows = []
    s = sg - UPSTREAM_M
    while s <= ss + 1e-6:
        lat, lon, nx, ny = point(s)
        side = lambda off: [anadem(lat + sgn * off * ny / KY, lon + sgn * off * nx / KX) for sgn in (1, -1)]
        a45, a90 = side(45.0), side(90.0)
        rows.append([round(s - sg), round(lat, 6), round(lon, 6), anadem(lat, lon),
                     min(v for v in a45 if v is not None), min(v for v in a90 if v is not None), glo30(lat, lon)])
        s += STEP_M
    c.write_csv(os.path.join(c.PROCESSED, "flood_run1_profile.csv"),
                ["m_from_gauge", "lat", "lon", "anadem_c", "anadem_45", "anadem_90", "glo30_c"],
                [[r[0], r[1], r[2]] + [None if v is None else round(v, 2) for v in r[3:]] for r in rows])

    # SVG chart (standard library only)
    W, H, L, R, T, B = 900, 380, 60, 20, 30, 50
    xs = [r[0] for r in rows]
    ys = [v for r in rows for v in r[3:7] if v is not None]
    y0, y1 = math.floor(min(ys)) - 1, math.ceil(max(ys)) + 1
    px = lambda x: L + (x - xs[0]) / (xs[-1] - xs[0]) * (W - L - R)
    py = lambda y: T + (y1 - y) / (y1 - y0) * (H - T - B)
    series = [(3, "#1f6feb", "ANADEM on the river line"), (4, "#2da44e", "ANADEM, lower bank at 45 m"),
              (5, "#8c959f", "ANADEM, lower bank at 90 m"), (6, "#cf222e", "GLO-30 surface model on the line")]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="sans-serif" font-size="12">' % (W, H),
           '<rect width="100%" height="100%" fill="white"/>',
           '<text x="%d" y="18" font-size="14">Rio Atibaia from 1.5 km above gauge 3E-063 to station 62671200: terrain along the river (m)</text>' % L]
    for yv in range(int(y0), int(y1) + 1, 2):
        svg.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#eee"/><text x="%d" y="%.1f" text-anchor="end">%d</text>'
                   % (L, W - R, py(yv), py(yv), L - 6, py(yv) + 4, yv))
    for xv in range(int(math.ceil(xs[0] / 1000.0)) * 1000, xs[-1] + 1, 1000):
        svg.append('<text x="%.1f" y="%d" text-anchor="middle">%g km</text>' % (px(xv), H - B + 18, xv / 1000.0))
    svg.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="#555" stroke-dasharray="4 3"/><text x="%.1f" y="%d">3E-063</text>'
               % (px(0), px(0), T, H - B, px(0) + 4, T + 12))
    for k, col, label in series:
        d = " ".join("%s%.1f,%.1f" % ("M" if i == 0 else "L", px(r[0]), py(r[k])) for i, r in enumerate(rows) if r[k] is not None)
        svg.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.5"/>' % (d, col))
    for i, (k, col, label) in enumerate(series):
        svg.append('<rect x="%d" y="%d" width="14" height="3" fill="%s"/><text x="%d" y="%d">%s</text>'
                   % (L + 10 + 210 * i, H - 14, col, L + 28 + 210 * i, H - 10, label))
    svg.append("</svg>")
    with open(os.path.join(c.ROOT, "docs", "flood_run1_profile.svg"), "w", encoding="utf-8") as f:
        f.write("\n".join(svg))

    near = [r for r in rows if abs(r[0]) <= 60]
    print("OSM line: %d points; gauge %.0f m and station %.0f m from it; reach %.1f km along the line"
          % (len(pts), dg, ds, (ss - sg) / 1000.0))
    for name, k in (("ANADEM on line", 3), ("ANADEM 45 m bank", 4), ("ANADEM 90 m bank", 5), ("GLO-30 on line", 6)):
        v = [r[k] for r in rows if r[k] is not None]
        print("%-17s start %.1f  at gauge %.1f  end %.1f  min %.1f  max %.1f"
              % (name, v[0], sum(r[k] for r in near) / len(near), v[-1], min(v), max(v)))
    print("ANADEM minus GLO-30 on the line: median %.1f m" % sorted(r[3] - r[6] for r in rows)[len(rows) // 2])


if __name__ == "__main__":
    main()
