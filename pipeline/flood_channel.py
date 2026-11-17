"""Channel widths, tributary inflow points and bank/bed profile for flood run 1.

Pre-run check 2 of docs/model_design_flood_run1.md (and the bank profile left
over from check 1). No radar image and no model output is used.

WIDTH RULE, fixed here before any width was computed (17 November 2026)
  The design says: width from OSM river polygons where mapped, otherwise
  measured on the August 2024 Sentinel-2 composite every 250 m, linear in
  between. OSM maps no river polygon in this reach, so every width is
  measured. The viewer's composite is a 20 m true-colour display image, too
  coarse for a river two to four pixels wide, so the measurement uses the
  same four scenes (tile 23KLQ; 3, 8, 18 and 23 August 2024) at their native
  10 m:
  - NDWI = (green - NIR) / (green + NIR) from bands B03 and B08, as surface
    reflectance (each scene's scale and offset from its catalogue entry);
    pixels masked where the scene classification (SCL, 20 m) is 0, 1, 3, 8, 9
    or 10, as in the viewer's composite; per pixel, the median NDWI over the
    unmasked scenes (at least two).
  - Water: median NDWI above 0.
  - Stations every 250 m along the OSM line of the Rio Atibaia, from 1.5 km
    above gauge 3E-063 to station 62671200. At each, a transect at right
    angles to the line, 60 m either side, sampled every 1 m (nearest pixel).
    The width is the length of the run of water samples that contains the
    line point or comes nearest to it, if within 20 m. No such run: no width.
    A run reaching the end of the transect: no width (not a river channel).
  - Between stations with a width, linear; before the first and after the
    last, the nearest width.
  - If fewer than half the stations have a width, the rule has failed.

  OUTCOME (17 November 2026): the rule failed; no station shows water (the
  river is narrower than a pixel or under riverside trees). The project lead
  then approved, before any model or image existed: channel width 11 m along
  the whole reach, from the OpenStreetMap `width` tag on the Rio Atibaia,
  with width x 0.67 and x 1.5 among the reported variations. This script
  records the failed measurement and then applies that width; it fetches the
  OSM tags once and keeps the response in data/raw/osm/.

TRIBUTARY POINTS (design: "the junctions found on the DEM")
  The five junctions on the 90 m flow path of the delineation DEM (GLO-30),
  recomputed here as in delineate.py, each moved to the nearest point of the
  OSM line, where the model's discharge point goes.

BANK AND BED (design rule)
  Every 30 m along the line: bank = the lower of ANADEM at (width / 2 + 30 m)
  either side of the line, "smoothed so it never rises downstream"; bed =
  bank - 2.11 m. Two readings of "smoothed so it never rises" are computed:
    running minimum   the lowest value so far from the upstream end (the
                      first reading, run on 17 November 2026: it follows the
                      lowest noise dips and sits a median 2.2 m below the
                      raw bank)
    isotonic          the least-squares fit that never rises downstream
                      (pool-adjacent-violators)
  BANK_RULE says which one feeds the model. The project lead chose the
  isotonic fit on 17 November 2026, before any model or image existed.

Outputs: data/raw/s2/ (band windows and catalogue entries, logged in the
manifest), data/processed/flood_run1_widths.csv, flood_run1_channel.csv,
flood_run1_tributaries.json, docs/flood_run1_channel.svg, and a summary.

Usage: python flood_channel.py
"""
import array
import heapq
import json
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
from cogread import read_window, utm_south  # noqa: E402

GAUGE = (-23.106111, -46.556389)      # 3E-063
STATION = (-23.1058, -46.5958)        # 62671200
UPSTREAM_M, STATION_STEP, PROFILE_STEP = 1500.0, 250.0, 30.0
HALF_TRANSECT, SEARCH_M, BANK_OFFSET, DEPTH = 60.0, 20.0, 30.0, 2.11
BANK_RULE = "isotonic"  # approved 17 November 2026; "running_min" is kept in the output for the record
SCENES = ["S2A_23KLQ_20240803_0_L2A", "S2B_23KLQ_20240808_0_L2A", "S2B_23KLQ_20240818_0_L2A", "S2A_23KLQ_20240823_0_L2A"]
MASKED_SCL = {0, 1, 3, 8, 9, 10}
STAC_ITEM = "https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/%s"
S2_SOURCE = "Sentinel-2 L2A COGs (ESA Copernicus) via Element 84 Earth Search"
S2_DIR = os.path.join(c.RAW, "s2")
OSM_QUERY = ('[out:json][timeout:60];way["waterway"="river"]["name"="Rio Atibaia"](-23.125,-46.61,-23.09,-46.54);'
             'out tags;')
OSM_FILE = os.path.join(c.RAW, "osm", "rio_atibaia_ways_flood_run1.json")
KX = 111320.0 * math.cos(math.radians(-23.1))
KY = 110574.0
ZONE = 23


# ---------- the OSM line ----------
def river_line():
    vec = json.load(open(os.path.join(c.ROOT, "web", "public", "data", "vectors.json"), encoding="utf-8"))
    seg = max((r for r in vec["rivers"] if (r.get("name") or "") == "Rio Atibaia"
               and min(p[0] for p in r["line"]) < STATION[1] + 0.01 and max(p[0] for p in r["line"]) > GAUGE[1] + 0.02),
              key=lambda r: len(r["line"]))
    pts = [(p[1], p[0]) for p in seg["line"]]
    if pts[0][1] < pts[-1][1]:
        pts.reverse()  # flows west: order from upstream (east)
    cum = [0.0]
    for (a, b), (c2, d) in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.hypot((d - b) * KX, (c2 - a) * KY))
    return pts, cum


def project(pts, cum, lat, lon):
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


def point(pts, cum, s):
    k = max(0, min(len(pts) - 2, next((i for i in range(len(cum) - 1) if cum[i + 1] >= s), len(cum) - 2)))
    (a, b), (c2, d) = pts[k], pts[k + 1]
    L = cum[k + 1] - cum[k] or 1.0
    t = (s - cum[k]) / L
    return a + t * (c2 - a), b + t * (d - b), -(c2 - a) * KY / L, (d - b) * KX / L  # lat, lon, normal (east, north)


def offset(lat, lon, nx, ny, d):
    return lat + d * ny / KY, lon + d * nx / KX


# ---------- ANADEM ----------
def anadem_sampler():
    base = os.path.join(c.RAW, "dem", "anadem_window")
    meta = json.load(open(base + ".json", encoding="utf-8"))
    z = array.array("f")
    z.frombytes(open(base + ".f32", "rb").read())
    bb, W, H = meta["bbox"], meta["width"], meta["height"]
    dx, dy = (bb["east"] - bb["west"]) / W, (bb["north"] - bb["south"]) / H

    def at(lat, lon):
        fx, fy = (lon - bb["west"]) / dx - 0.5, (bb["north"] - lat) / dy - 0.5
        x0, y0 = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - x0, fy - y0
        v = [z[(y0 + j) * W + x0 + i] for j in (0, 1) for i in (0, 1)]
        return (v[0] * (1 - tx) + v[1] * tx) * (1 - ty) + (v[2] * (1 - tx) + v[3] * tx) * ty
    return at


# ---------- Sentinel-2 ----------
def s2_windows(x0, y0, x1, y1):
    """B03, B08 (10 m) and SCL (20 m) windows for each scene, cached in data/raw/s2/."""
    c.ensure_dir(S2_DIR)
    scenes = []
    for sid in SCENES:
        meta_path = os.path.join(S2_DIR, sid + ".json")
        if os.path.exists(meta_path):
            scenes.append(json.load(open(meta_path, encoding="utf-8")))
            continue
        url = STAC_ITEM % sid
        data = c.http_get(url, timeout=120)
        c.write_bytes(os.path.join(S2_DIR, sid + "_item.json"), data)
        c.append_manifest({"source": S2_SOURCE, "url": url, "file": "data/raw/s2/%s_item.json" % sid,
                           "bytes": len(data), "sha256": c.sha256(data)})
        item = json.loads(data.decode("utf-8"))
        rec = {"id": sid, "datetime": item["properties"]["datetime"],
               "boa_offset_applied": item["properties"].get("earthsearch:boa_offset_applied"), "bands": {}}
        for band, key in (("B03", "green"), ("B08", "nir"), ("SCL", "scl")):
            asset = item["assets"][key]
            rb = (asset.get("raster:bands") or [{}])[0]
            vals, w, h, grid = read_window(asset["href"], x0, y0, x1, y1, S2_SOURCE, note="%s %s window for flood run 1" % (sid, band))
            code = "B" if band == "SCL" else "H"
            arr = array.array(code, vals)
            fn = "%s_%s.%s" % (sid, band, "u8" if code == "B" else "u16")
            with open(os.path.join(S2_DIR, fn), "wb") as f:
                arr.tofile(f)
            rec["bands"][band] = {"file": fn, "href": asset["href"], "width": w, "height": h,
                                  "x0": grid["x0"], "y0": grid["y0"], "res": grid["res_x"],
                                  "scale": rb.get("scale"), "offset": rb.get("offset"), "nodata": rb.get("nodata"),
                                  "tiles": grid["tiles"], "sha256_window": c.sha256(arr.tobytes())}
            print("  ", sid, band, "%d x %d" % (w, h), "tiles:", len(grid["tiles"]), flush=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=1)
        scenes.append(rec)
    return scenes


def load_band(b, code):
    a = array.array(code)
    a.frombytes(open(os.path.join(S2_DIR, b["file"]), "rb").read())
    return a


def median_ndwi(scenes):
    g0 = scenes[0]["bands"]["B03"]
    W, H, X0, Y0, R = g0["width"], g0["height"], g0["x0"], g0["y0"], g0["res"]
    stack = []
    for s in scenes:
        g, n, scl = s["bands"]["B03"], s["bands"]["B08"], s["bands"]["SCL"]
        assert (g["x0"], g["y0"], g["width"], g["height"]) == (X0, Y0, W, H) == (n["x0"], n["y0"], n["width"], n["height"])
        G, N, S = load_band(g, "H"), load_band(n, "H"), load_band(scl, "B")
        # Earth Search marks scenes whose values already carry the BOA offset (earthsearch:boa_offset_applied);
        # their raster:bands still list the offset, and applying it again gives negative reflectance.
        # (First run, 17 November 2026: offset applied twice, NDWI out of [-1, 1]; fixed before any width was used.)
        already = s.get("boa_offset_applied") is True
        gs, go = g["scale"] or 1e-4, 0.0 if already else (g["offset"] or 0.0)
        ns, no = n["scale"] or 1e-4, 0.0 if already else (n["offset"] or 0.0)
        out = [None] * (W * H)
        for r in range(H):
            sr = int((Y0 - r * R - 0.5 * R - scl["y0"]) / -scl["res"])
            for col in range(W):
                sc = int((X0 + col * R + 0.5 * R - scl["x0"]) / scl["res"])
                i = r * W + col
                if not (0 <= sr < scl["height"] and 0 <= sc < scl["width"]) or S[sr * scl["width"] + sc] in MASKED_SCL:
                    continue
                if G[i] == 0 or N[i] == 0:
                    continue
                gr, nr = G[i] * gs + go, N[i] * ns + no
                if gr > 0 and nr > 0:  # reflectance must be positive; anything else is a defect, left out
                    out[i] = (gr - nr) / (gr + nr)
        v = [x for x in out if x is not None]
        if v and (min(v) < -1.0 or max(v) > 1.0):
            raise SystemExit("NDWI outside [-1, 1] in %s: reflectance scaling is wrong" % s["id"])
        stack.append(out)
    med = [None] * (W * H)
    counts = [0] * (W * H)
    for i in range(W * H):
        v = [s[i] for s in stack if s[i] is not None]
        counts[i] = len(v)
        if len(v) >= 2:
            med[i] = statistics.median(v)
    return med, counts, (W, H, X0, Y0, R)


# ---------- the approved width: the OSM width tag ----------
def osm_width():
    """The `width` tag of the Rio Atibaia ways through the reach (Overpass, fetched once and kept)."""
    if not os.path.exists(OSM_FILE):
        url = "https://overpass-api.de/api/interpreter"
        import time
        import urllib.parse
        import urllib.request
        last = None
        for k in range(4):
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": OSM_QUERY}).encode(),
                                             headers={"User-Agent": c.USER_AGENT})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                break
            except Exception as e:  # Overpass refuses when busy; wait and retry
                last = e
                time.sleep(20 * (k + 1))
        else:
            raise last
        c.write_bytes(OSM_FILE, data)
        c.append_manifest({"source": "OpenStreetMap contributors via Overpass API", "url": url, "query": OSM_QUERY,
                           "file": os.path.relpath(OSM_FILE, c.ROOT).replace("\\", "/"), "bytes": len(data),
                           "sha256": c.sha256(data)})
    ways = json.load(open(OSM_FILE, encoding="utf-8"))["elements"]
    widths = {w["id"]: w.get("tags", {}).get("width") for w in ways}
    vals = {float(v) for v in widths.values() if v}
    if len(vals) != 1:
        raise SystemExit("expected one OSM width on the Rio Atibaia ways, found %s" % widths)
    return vals.pop(), widths


# ---------- the 90 m flow path and its junctions ----------
def dem_junctions():
    base = os.path.join(c.RAW, "dem", "delineation")
    meta = json.load(open(base + ".json", encoding="utf-8"))
    W, H, bb = meta["width"], meta["height"], meta["bbox"]
    z = array.array("f")
    z.frombytes(open(base + ".f32", "rb").read())
    n = W * H
    NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    filled, down, seen, heap = [0.0] * n, [-1] * n, bytearray(n), []
    for r in range(H):
        for col in range(W):
            if r in (0, H - 1) or col in (0, W - 1):
                i = r * W + col
                seen[i] = 1
                filled[i] = z[i]
                heap.append((z[i], i))
    heapq.heapify(heap)
    while heap:
        h, i = heapq.heappop(heap)
        r, col = divmod(i, W)
        for dr, dc in NB:
            rr, cc = r + dr, col + dc
            if 0 <= rr < H and 0 <= cc < W and not seen[rr * W + cc]:
                j = rr * W + cc
                seen[j] = 1
                filled[j] = z[j] if z[j] > h else h + 1e-4
                down[j] = i
                heapq.heappush(heap, (filled[j], j))
    acc = [1] * n
    for i in sorted(range(n), key=filled.__getitem__, reverse=True):
        if down[i] >= 0:
            acc[down[i]] += acc[i]
    dlat, dlon = (bb["north"] - bb["south"]) / H, (bb["east"] - bb["west"]) / W

    def km2(i):
        lat = bb["north"] - (i // W + 0.5) * dlat
        return acc[i] * (dlat * 110.574) * (dlon * 111.320 * math.cos(math.radians(lat)))

    def ll(i):
        r, col = divmod(i, W)
        return bb["north"] - (r + 0.5) * dlat, bb["west"] + (col + 0.5) * dlon

    def snap(lat, lon, k=6):
        r0, c0 = int((bb["north"] - lat) / dlat), int((lon - bb["west"]) / dlon)
        return max((r * W + cc for r in range(r0 - k, r0 + k + 1) for cc in range(c0 - k, c0 + k + 1)), key=acc.__getitem__)
    children = {}
    for i in range(n):
        if down[i] >= 0:
            children.setdefault(down[i], []).append(i)
    g, p = snap(*GAUGE), snap(*STATION)
    out, i, prev = [], g, None
    while i != p and down[i] >= 0:
        if prev is not None:
            for ch in children.get(i, []):
                if ch != prev and km2(ch) >= 2.0:
                    la, lo = ll(i)
                    out.append({"area_km2": round(km2(ch), 1), "dem_lat": round(la, 5), "dem_lon": round(lo, 5)})
        prev, i = i, down[i]
    return out


def main():
    pts, cum = river_line()
    _, sg = project(pts, cum, *GAUGE)
    _, ss = project(pts, cum, *STATION)
    anadem = anadem_sampler()

    # window: the reach's line points plus 300 m, in UTM 23S
    sel = [p for p, s in zip(pts, cum) if sg - UPSTREAM_M - 500 <= s <= ss + 500]
    xy = [utm_south(a, b, ZONE) for a, b in sel]
    x0, x1 = min(x for x, _ in xy) - 300, max(x for x, _ in xy) + 300
    y0, y1 = min(y for _, y in xy) - 300, max(y for _, y in xy) + 300
    print("Sentinel-2 window (UTM 23S): %.0f-%.0f E, %.0f-%.0f N" % (x0, x1, y0, y1), flush=True)
    scenes = s2_windows(x0, y0, x1, y1)
    med, counts, (W, H, X0, Y0, R) = median_ndwi(scenes)

    def water_at(lat, lon):
        x, y = utm_south(lat, lon, ZONE)
        col, row = int((x - X0) // R), int((Y0 - y) // R)
        if not (0 <= col < W and 0 <= row < H):
            return None
        v = med[row * W + col]
        return None if v is None else v > 0.0

    # widths at the stations
    stations = []
    s = sg - UPSTREAM_M
    while s <= ss + 1e-6:
        lat, lon, nx, ny = point(pts, cum, s)
        samples = []
        for k in range(int(-HALF_TRANSECT), int(HALF_TRANSECT) + 1):
            samples.append((k, water_at(*offset(lat, lon, nx, ny, k))))
        runs, cur = [], None
        for k, w in samples:
            if w:
                cur = [k, k] if cur is None else [cur[0], k]
            elif cur is not None:
                runs.append(cur)
                cur = None
        if cur is not None:
            runs.append(cur)
        best = None
        for a, b in runs:
            dist = 0 if a <= 0 <= b else min(abs(a), abs(b))
            if dist <= SEARCH_M and (best is None or dist < best[0]):
                best = (dist, a, b)
        width, why = None, ""
        if best is None:
            why = "no water within %d m of the line" % SEARCH_M
        elif best[1] <= -HALF_TRANSECT or best[2] >= HALF_TRANSECT:
            why = "water run reaches the transect end"
        else:
            width = best[2] - best[1] + 1
        unk = sum(1 for _, w in samples if w is None)
        stations.append({"m_from_gauge": round(s - sg), "lat": round(lat, 6), "lon": round(lon, 6),
                         "width_m": width, "offset_m": None if best is None else best[0], "unknown_samples": unk, "why": why})
        s += STATION_STEP
    measured = [st for st in stations if st["width_m"] is not None]
    print("stations: %d, with a width: %d" % (len(stations), len(measured)))

    def ndwi_line(st):  # median NDWI within 10 m of the line point, for the record
        lat, lon = st["lat"], st["lon"]
        vals = []
        for dlat in (-10, 0, 10):
            for dlon in (-10, 0, 10):
                x, y = utm_south(lat + dlat / KY, lon + dlon / KX, ZONE)
                col, row = int((x - X0) // R), int((Y0 - y) // R)
                if 0 <= col < W and 0 <= row < H and med[row * W + col] is not None:
                    vals.append(med[row * W + col])
        return round(max(vals), 3) if vals else None
    c.write_csv(os.path.join(c.PROCESSED, "flood_run1_widths.csv"),
                ["m_from_gauge", "lat", "lon", "width_m", "run_offset_m", "samples_without_data", "max_ndwi_within_10m", "why_no_width"],
                [[st["m_from_gauge"], st["lat"], st["lon"], st["width_m"], st["offset_m"], st["unknown_samples"], ndwi_line(st), st["why"]]
                 for st in stations])

    # tributary inflow points (independent of the widths)
    tribs = []
    for j in dem_junctions():
        dist, s_on = project(pts, cum, j["dem_lat"], j["dem_lon"])
        lat, lon, _, _ = point(pts, cum, s_on)
        x, y = utm_south(lat, lon, ZONE)
        j.update({"m_from_gauge": round(s_on - sg), "lat": round(lat, 6), "lon": round(lon, 6),
                  "utm23s_e": round(x, 1), "utm23s_n": round(y, 1), "moved_m": round(dist)})
        tribs.append(j)
    with open(os.path.join(c.PROCESSED, "flood_run1_tributaries.json"), "w", encoding="utf-8") as f:
        json.dump({"rule": "junctions on the 90 m flow path of the delineation DEM (>= 2 km2), moved to the nearest "
                           "point of the OSM line of the Rio Atibaia", "points": tribs}, f, indent=1)
    for t in tribs:
        print("tributary %5.1f km2 at %5d m below the gauge (moved %d m onto the line)" % (t["area_km2"], t["m_from_gauge"], t["moved_m"]))

    if len(measured) < len(stations) / 2:
        lines = [v for v in (ndwi_line(st) for st in stations) if v is not None]
        print("highest NDWI within 10 m of the line, by station: median %.2f, max %.2f (water needs > 0)"
              % (statistics.median(lines), max(lines)))
        print("WIDTH RULE FAILED: fewer than half the stations have a width.")
        osm_w, osm_ways = osm_width()
        print("approved change (17 November 2026): OSM width tag, %.0f m on ways %s" % (osm_w, sorted(osm_ways)))
        width_source = "OSM width tag (%.0f m), approved after the Sentinel-2 rule failed" % osm_w

        def width_at(m):
            return osm_w
    else:
        width_source = "Sentinel-2 NDWI, measured"

        def width_at(m):
            ms = [(st["m_from_gauge"], st["width_m"]) for st in measured]
            if m <= ms[0][0]:
                return ms[0][1]
            if m >= ms[-1][0]:
                return ms[-1][1]
            for (a, wa), (b, wb) in zip(ms, ms[1:]):
                if a <= m <= b:
                    return wa + (wb - wa) * (m - a) / (b - a)

    # bank and bed every 30 m: raw bank, then both monotone readings
    rows, s, run_min = [], sg - UPSTREAM_M, None
    while s <= ss + 1e-6:
        lat, lon, nx, ny = point(pts, cum, s)
        m = s - sg
        w = width_at(m)
        d = w / 2 + BANK_OFFSET
        bank_raw = min(anadem(*offset(lat, lon, nx, ny, d)), anadem(*offset(lat, lon, nx, ny, -d)))
        run_min = bank_raw if run_min is None else min(run_min, bank_raw)
        rows.append([m, lat, lon, w, anadem(lat, lon), bank_raw, run_min])
        s += PROFILE_STEP
    blocks = []  # isotonic regression, non-increasing downstream (pool adjacent violators)
    for r in rows:
        blocks.append([r[5], 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] < blocks[-1][0] / blocks[-1][1]:
            sm, n = blocks.pop()
            blocks[-1][0] += sm
            blocks[-1][1] += n
    iso = [sm / n for sm, n in blocks for _ in range(n)]
    prof = []
    for r, b_iso in zip(rows, iso):
        chosen = {"running_min": r[6], "isotonic": b_iso}.get(BANK_RULE)
        prof.append([round(r[0]), round(r[1], 6), round(r[2], 6), round(r[3], 1), round(r[4], 2), round(r[5], 2),
                     round(r[6], 2), round(b_iso, 2), None if chosen is None else round(chosen, 2),
                     None if chosen is None else round(chosen - DEPTH, 2)])
    c.write_csv(os.path.join(c.PROCESSED, "flood_run1_channel.csv"),
                ["m_from_gauge", "lat", "lon", "width_m", "anadem_line", "bank_raw", "bank_running_min", "bank_isotonic",
                 "bank", "bed"], prof)

    # chart
    Wd, Hd, L, Rm, T = 900, 520, 60, 20, 30
    xs = [p[0] for p in prof]
    px = lambda v: L + (v - xs[0]) / (xs[-1] - xs[0]) * (Wd - L - Rm)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="sans-serif" font-size="12">' % (Wd, Hd),
           '<rect width="100%" height="100%" fill="white"/>',
           '<text x="%d" y="18" font-size="14">Rio Atibaia, 1.5 km above 3E-063 to 62671200: channel width (top) and bank and bed (bottom)</text>' % L,
           '<text x="%d" y="34" fill="#555">Width: %s. Red x: no water seen by Sentinel-2 at that station.</text>' % (L, width_source)]
    # widths panel (y 40-200)
    wmax = max([p[3] for p in prof] + [st["width_m"] for st in measured] + [10]) + 10
    py1 = lambda v: 200 - v / wmax * 150
    for v in range(0, int(wmax) + 1, 20):
        svg.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#eee"/><text x="%d" y="%.1f" text-anchor="end">%d m</text>' % (L, Wd - Rm, py1(v), py1(v), L - 6, py1(v) + 4, v))
    svg.append('<path d="%s" fill="none" stroke="#1f6feb" stroke-width="1.5"/>' % " ".join(
        "%s%.1f,%.1f" % ("M" if i == 0 else "L", px(p[0]), py1(p[3])) for i, p in enumerate(prof)))
    for st in stations:
        if st["width_m"] is not None:
            svg.append('<circle cx="%.1f" cy="%.1f" r="3" fill="#1f6feb"/>' % (px(st["m_from_gauge"]), py1(st["width_m"])))
        else:
            svg.append('<text x="%.1f" y="%.1f" text-anchor="middle" fill="#cf222e">x</text>' % (px(st["m_from_gauge"]), py1(0) + 4))
    # profile panel (y 240-470)
    ys = [v for p in prof for v in (p[4], p[5], p[6] - DEPTH, p[7] - DEPTH)]
    lo, hi = math.floor(min(ys)) - 1, math.ceil(max(ys)) + 1
    py2 = lambda v: 470 - (v - lo) / (hi - lo) * 220
    for v in range(int(lo), int(hi) + 1, 2):
        svg.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#eee"/><text x="%d" y="%.1f" text-anchor="end">%d</text>' % (L, Wd - Rm, py2(v), py2(v), L - 6, py2(v) + 4, v))
    series = ((lambda p: p[4], "#8c959f", "", "ANADEM on the line"), (lambda p: p[5], "#d4a72c", "", "bank, raw"),
              (lambda p: p[6], "#cf222e", "", "bank: running minimum"), (lambda p: p[7], "#2da44e", "", "bank: isotonic"),
              (lambda p: p[6] - DEPTH, "#cf222e", "4 3", "bed (running min)"), (lambda p: p[7] - DEPTH, "#2da44e", "4 3", "bed (isotonic)"))
    for k, (f, col, dash, lab) in enumerate(series):
        svg.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.5"%s/>' % (" ".join(
            "%s%.1f,%.1f" % ("M" if i == 0 else "L", px(p[0]), py2(f(p))) for i, p in enumerate(prof)), col,
            ' stroke-dasharray="%s"' % dash if dash else ""))
        svg.append('<rect x="%d" y="%d" width="14" height="3" fill="%s"/><text x="%d" y="%d">%s</text>'
                   % (L + 10 + 140 * k, Hd - 18, col, L + 28 + 140 * k, Hd - 14, lab))
    for t in tribs:
        svg.append('<line x1="%.1f" x2="%.1f" y1="240" y2="470" stroke="#cf222e" stroke-dasharray="3 3"/><text x="%.1f" y="252" fill="#cf222e">%g km²</text>'
                   % (px(t["m_from_gauge"]), px(t["m_from_gauge"]), px(t["m_from_gauge"]) + 3, t["area_km2"]))
    svg.append('<line x1="%.1f" x2="%.1f" y1="40" y2="470" stroke="#555" stroke-dasharray="4 3"/><text x="%.1f" y="52">3E-063</text>' % (px(0), px(0), px(0) + 4))
    for v in range(int(math.ceil(xs[0] / 1000.0)) * 1000, xs[-1] + 1, 1000):
        svg.append('<text x="%.1f" y="488" text-anchor="middle">%g km</text>' % (px(v), v / 1000.0))
    svg.append("</svg>")
    with open(os.path.join(c.ROOT, "docs", "flood_run1_channel.svg"), "w", encoding="utf-8") as f:
        f.write("\n".join(svg))

    print("width source:", width_source)
    if measured:
        ws = [st["width_m"] for st in measured]
        print("measured widths (m): median %.0f, range %d-%d" % (statistics.median(ws), min(ws), max(ws)))
    print("stations without a Sentinel-2 width: %d of %d" % (len(stations) - len(measured), len(stations)))
    g = min(range(len(prof)), key=lambda i: abs(prof[i][0]))
    print("bank, raw: %.1f-%.1f m" % (min(p[5] for p in prof), max(p[5] for p in prof)))
    for k, name in ((6, "running minimum"), (7, "isotonic")):
        d = sorted(p[5] - p[k] for p in prof)
        print("bank, %-15s top %.2f, at the gauge %.2f, end %.2f m; raw minus it: median %+.2f (p10 %+.2f, p90 %+.2f)"
              % (name, prof[0][k], prof[g][k], prof[-1][k], statistics.median(d), d[len(d) // 10], d[9 * len(d) // 10]))
    print("bank rule feeding the model:", BANK_RULE or "NOT DECIDED")
    print("pixels with fewer than two clear scenes in the window: %d of %d" % (sum(1 for v in counts if v < 2), len(counts)))


if __name__ == "__main__":
    main()
