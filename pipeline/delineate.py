"""Delineate catchments from the DEM window and check their areas against the
drainage areas published by ANA for the same points.

Method: priority-flood depression filling (Barnes et al. 2014) with a tiny
gradient so flats drain, D8 flow directions, flow accumulation, then the set
of cells draining to each outlet. Outlets are snapped to the cell with the
largest accumulation within SNAP cells of the published coordinates.

The DEM is Copernicus GLO-30 sampled at 3 arc-seconds. It is a surface model,
so divides under forest are slightly uncertain; the area check is the test.

Usage: python delineate.py
Outputs: data/processed/catchments.json (masks as row runs), a table printed
and stored for the report, and web/public/data/catchments.json (outlines).
"""
import array
import heapq
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

DEM = os.path.join(c.RAW, "dem", "delineation")
SNAP = 6
# name, lat, lon, published drainage area (km2), source of the published figure
OUTLETS = [
    ("cachoeira_dam", -23.0508, -46.3192, 392.0, "ANA inventory, station 62666010"),
    ("atibainha_dam", -23.1739, -46.3900, 312.0, "ANA inventory, station 62653510"),
    ("piracaia_gauge", -23.0517, -46.3653, 431.0, "ANA inventory, station 62665000"),
    ("nazare_gauge", -23.1664, -46.4161, 358.0, "ANA inventory, station 62662000"),
    ("atibaia_gauge", -23.1056, -46.5569, 1140.0, "ANA inventory, station 62670000"),
]
NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def main():
    meta = json.load(open(DEM + ".json", encoding="utf-8"))
    W, H = meta["width"], meta["height"]
    bb = meta["bbox"]
    z = array.array("f")
    with open(DEM + ".f32", "rb") as f:
        z.frombytes(f.read())
    n = W * H
    assert len(z) == n

    # priority flood from the window edge, recording the cell each cell drains to
    filled = [0.0] * n
    down = [-1] * n
    seen = bytearray(n)
    heap = []
    for r in range(H):
        for col in range(W):
            if r in (0, H - 1) or col in (0, W - 1):
                i = r * W + col
                seen[i] = 1
                filled[i] = z[i]
                heap.append((z[i], i))
    heapq.heapify(heap)
    eps = 1e-4
    while heap:
        h, i = heapq.heappop(heap)
        r, col = divmod(i, W)
        for dr, dc in NB:
            rr, cc = r + dr, col + dc
            if rr < 0 or rr >= H or cc < 0 or cc >= W:
                continue
            j = rr * W + cc
            if seen[j]:
                continue
            seen[j] = 1
            hj = z[j] if z[j] > h else h + eps
            filled[j] = hj
            down[j] = i  # first reached from i: i lies on j's path to the edge
            heapq.heappush(heap, (hj, j))

    # accumulation in cells, processed from high to low filled elevation
    order = sorted(range(n), key=filled.__getitem__, reverse=True)
    acc = [1] * n
    for i in order:
        d = down[i]
        if d >= 0:
            acc[d] += acc[i]

    dlat = (bb["north"] - bb["south"]) / H
    dlon = (bb["east"] - bb["west"]) / W

    def cell_km2(r):
        lat = bb["north"] - (r + 0.5) * dlat
        return (dlat * 110.574) * (dlon * 111.320 * math.cos(math.radians(lat)))

    children = [[] for _ in range(n)]
    for i in range(n):
        if down[i] >= 0:
            children[down[i]].append(i)

    results = {}
    table = []
    for name, lat, lon, published, src in OUTLETS:
        r0 = int((bb["north"] - lat) / dlat)
        c0 = int((lon - bb["west"]) / dlon)
        best = None
        for r in range(max(0, r0 - SNAP), min(H, r0 + SNAP + 1)):
            for col in range(max(0, c0 - SNAP), min(W, c0 + SNAP + 1)):
                i = r * W + col
                if best is None or acc[i] > acc[best]:
                    best = i
        mask = bytearray(n)
        stack = [best]
        mask[best] = 1
        while stack:
            i = stack.pop()
            for j in children[i]:
                if not mask[j]:
                    mask[j] = 1
                    stack.append(j)
        area = 0.0
        touches_edge = False
        runs = []
        sum_lat = sum_lon = cells = 0
        for r in range(H):
            row = mask[r * W:(r + 1) * W]
            k = row.count(1)
            if not k:
                continue
            area += k * cell_km2(r)
            if r in (0, H - 1) or row[0] or row[-1]:
                touches_edge = True
            col = 0
            while col < W:
                if row[col]:
                    start = col
                    while col < W and row[col]:
                        col += 1
                    runs.append([r, start, col - 1])
                    sum_lon += (start + col - 1) / 2.0 * (col - start)
                else:
                    col += 1
            sum_lat += r * k
            cells += k
        br, bc = divmod(best, W)
        results[name] = {
            "area_km2": round(area, 1), "published_km2": published, "published_source": src,
            "difference_pct": round((area - published) / published * 100.0, 1),
            "outlet": {"lat": round(bb["north"] - (br + 0.5) * dlat, 5), "lon": round(bb["west"] + (bc + 0.5) * dlon, 5)},
            "centroid": {"lat": round(bb["north"] - (sum_lat / cells + 0.5) * dlat, 4),
                         "lon": round(bb["west"] + (sum_lon / cells + 0.5) * dlon, 4)},
            "touches_window_edge": touches_edge, "runs": runs,
        }
        table.append((name, area, published, (area - published) / published * 100.0, touches_edge))
        print("%-16s delineated %7.1f km2   published %7.1f km2   difference %+5.1f%%%s" %
              (name, area, published, (area - published) / published * 100.0,
               "   TOUCHES WINDOW EDGE" if touches_edge else ""), flush=True)

    out = {"dem": meta, "method": "priority-flood fill, D8, snap %d cells" % SNAP, "catchments": results}
    c.ensure_dir(c.PROCESSED)
    with open(os.path.join(c.PROCESSED, "catchments.json"), "w", encoding="utf-8") as f:
        json.dump(out, f)

    # outlines for the viewer: boundary cell edges as short segments (lon, lat)
    web = {"source": "Delineated in pipeline/delineate.py from Copernicus DEM GLO-30 at 3 arc-seconds",
           "catchments": {}}
    for name, res in results.items():
        mask = bytearray(n)
        for r, a, b in res["runs"]:
            for col in range(a, b + 1):
                mask[r * W + col] = 1
        segs = []
        for r, a, b in res["runs"]:
            lat_n = bb["north"] - r * dlat
            lat_s = lat_n - dlat
            for col in range(a, b + 1):
                lon_w = bb["west"] + col * dlon
                lon_e = lon_w + dlon
                if r == 0 or not mask[(r - 1) * W + col]:
                    segs.append([lon_w, lat_n, lon_e, lat_n])
                if r == H - 1 or not mask[(r + 1) * W + col]:
                    segs.append([lon_w, lat_s, lon_e, lat_s])
                if col == 0 or not mask[r * W + col - 1]:
                    segs.append([lon_w, lat_n, lon_w, lat_s])
                if col == W - 1 or not mask[r * W + col + 1]:
                    segs.append([lon_e, lat_n, lon_e, lat_s])
        web["catchments"][name] = {"area_km2": res["area_km2"], "published_km2": res["published_km2"],
                                   "segments": [[round(v, 5) for v in s] for s in segs]}
    web_dir = os.path.join(c.ROOT, "web", "public", "data")
    c.ensure_dir(web_dir)
    with open(os.path.join(web_dir, "catchments.json"), "w", encoding="utf-8") as f:
        json.dump(web, f, separators=(",", ":"))


if __name__ == "__main__":
    main()
