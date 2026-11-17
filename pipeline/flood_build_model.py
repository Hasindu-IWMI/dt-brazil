"""Build the SFINCS model of flood run 1 and run the design's steady test.

docs/model_design_flood_run1.md, "Terrain: the 5 m composite", "Reach, grid
and software" and pre-run check 5. Uses no radar image and no observed flood.
Run with the atibaia-sfincs environment (envs/flood-sfincs.yml; on this
machine with OSGeo4W removed from PATH, see that file).

Steps
  1. Domain, on ANADEM (30 m): cells no more than 15 m above the river (height
     above nearest drainage, the drainage being the OSM line of the Rio
     Atibaia: in this window ANADEM's own flow paths cannot reach the 1,000 km2
     threshold, the river's catchment lying mostly outside it) and within 2 km
     of the line, between 1.5 km above gauge 3E-063 and station 62671200;
     the connected part that touches the river.
  2. Composite terrain, 5 m, SIRGAS 2000 / UTM 23S (EPSG:31983): ANADEM
     resampled bilinearly; the channel cut in (pixels within half the 11 m
     width of the line set to the bed of data/processed/flood_run1_channel.csv);
     buildings raised by 10 m (OSM footprints, plus Microsoft footprints that
     do not overlap an OSM one; not over the channel).
  3. Roughness, 5 m: WorldCover class -> Manning n (design table); channel
     pixels -> the channel n (the one calibrated parameter).
  4. SFINCS model with HydroMT-SFINCS 2.0.0: regular 25 m grid, active cells =
     the domain, water-level boundary cells at the downstream end, subgrid
     tables from the 5 m layers (5 x 5 pixels per cell).
  5. Forcing written as plain text: discharge at the upstream end and at the
     four tributary points, water level at the boundary, observation points,
     a cross-section across the valley at the gauge.

Steady test (check 5): 15 m3/s at the upstream end, no tributary flow, a
constant downstream level, 24 hours. Pass: every observation point's level
changes by less than 1 cm over the last 2 hours, and the discharge through the
cross-section at the gauge is within 5% of 15 m3/s. The downstream level used
is PROVISIONAL (bed at the station + the depth that 15 m3/s gives at the
gauge by SP Aguas' rating): the design's datum tie for that station could not
be applied (see the addendum). It tests the boundary's behaviour, not its
level.

Usage: python pipeline/flood_build_model.py [--n 0.035] [--hours 120] [--out models/flood_run1/steady_15]

Diagnostic switches (environment variables; NOT part of the design, used on
17 November 2026 to find why the channel carries too little water):
  FLOOD_DX      compute cell size (default 25)
  FLOOD_SUB     subgrid pixels per cell (even; default 6 at 25 m)
  FLOOD_NLEV    subgrid levels (default 10)
  FLOOD_WEIGHT  subgrid weight_option: min (default), mean or all
  FLOOD_DIAG    nobuildings, or confined (everything but the channel raised 20 m)
Finding: with the channel alone open, 15 m3/s stands 5.2-8.6 m deep at the
gauge on 25, 10 and 5 m grids, against about 1.95 m by Manning's equation for
an 11 m channel at the reach's slope. See the design's pre-run addendum.
"""
import argparse
import glob
import gzip
import json
import math
import os
import subprocess
import sys

import geopandas as gpd
import netCDF4
import numpy as np
import pyflwdir
import rasterio
import shapely
from pyproj import Transformer
from rasterio import features
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from scipy import ndimage
from shapely.geometry import LineString, Point, box, shape
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, PROC = os.path.join(ROOT, "data", "raw"), os.path.join(ROOT, "data", "processed")
IMAGE = "deltares/sfincs-cpu:sfincs-v2.5.0-Hautacam"
EPSG = 31983
DX, PIX = float(os.environ.get("FLOOD_DX", "25")), 5.0  # compute cell and composite-terrain pixel (m); the design fixes 25 m
SUB = int(os.environ["FLOOD_SUB"]) if os.environ.get("FLOOD_SUB") else (int(round(DX / 4.1667)) if DX == 25.0 else int(round(DX / PIX)))  # subgrid pixels per cell: HydroMT-SFINCS needs an even number
                                       # tables use 25/6 = 4.2 m pixels resampled from the 5 m composite
WIDTH, LIFT_BUILDINGS = 11.0, 10.0
HAND_MAX, LATERAL_MAX = 15.0, 2000.0
GAUGE = (-23.106111, -46.556389)       # 3E-063 (lat, lon)
STATION = (-23.1058, -46.5958)         # 62671200
OVERFLOW_M, H0_M = 3.01, 0.90          # 3E-063 overflow level and zero-flow stage (gauge scale)
MANNING = {10: 0.10, 20: 0.07, 30: 0.035, 40: 0.035, 50: 0.05, 60: 0.03, 70: 0.035, 80: 0.03, 90: 0.06, 95: 0.06, 100: 0.035}
TO_UTM = Transformer.from_crs(4326, EPSG, always_xy=True)
TO_LL = Transformer.from_crs(EPSG, 4326, always_xy=True)


def river_line_utm():
    vec = json.load(open(os.path.join(ROOT, "web", "public", "data", "vectors.json"), encoding="utf-8"))
    seg = max((r for r in vec["rivers"] if (r.get("name") or "") == "Rio Atibaia"
               and min(p[0] for p in r["line"]) < STATION[1] + 0.01 and max(p[0] for p in r["line"]) > GAUGE[1] + 0.02),
              key=lambda r: len(r["line"]))
    pts = seg["line"]
    if pts[0][0] < pts[-1][0]:
        pts = pts[::-1]  # upstream (east) first
    x, y = TO_UTM.transform([p[0] for p in pts], [p[1] for p in pts])
    return LineString(list(zip(x, y))), LineString([(p[0], p[1]) for p in pts])


def utm_point(lat, lon):
    return Point(*TO_UTM.transform(lon, lat))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=float, default=0.035, help="channel Manning n")
    ap.add_argument("--out", default=os.path.join(ROOT, "models", "flood_run1", "steady_15"))
    ap.add_argument("--no-run", action="store_true")
    ap.add_argument("--hours", type=int, default=120, help="steady-test duration (24 h and 72 h were not long enough)")
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    terr = os.path.join(ROOT, "models", "flood_run1", "terrain")
    os.makedirs(terr, exist_ok=True)

    line, line_ll = river_line_utm()
    s_gauge = line.project(utm_point(*GAUGE))
    s_station = line.project(utm_point(*STATION))
    prof = [r.split(",") for r in open(os.path.join(PROC, "flood_run1_channel.csv"), encoding="utf-8").read().splitlines()]
    head, rows = prof[0], prof[1:]
    ilat, ilon, ibed, ibank = head.index("lat"), head.index("lon"), head.index("bed"), head.index("bank")
    s_prof = np.array([line.project(utm_point(float(r[ilat]), float(r[ilon]))) for r in rows])
    bed_prof = np.array([float(r[ibed]) for r in rows])
    bank_prof = np.array([float(r[ibank]) for r in rows])
    order = np.argsort(s_prof)
    s_prof, bed_prof, bank_prof = s_prof[order], bed_prof[order], bank_prof[order]
    s_start = s_prof[0]
    print("line: gauge at %.0f m, station at %.0f m, profile %.0f-%.0f m" % (s_gauge, s_station, s_prof[0], s_prof[-1]), flush=True)

    # ---- 1. domain on ANADEM
    meta = json.load(open(os.path.join(RAW, "dem", "anadem_window.json"), encoding="utf-8"))
    bb, W, H = meta["bbox"], meta["width"], meta["height"]
    z = np.fromfile(os.path.join(RAW, "dem", "anadem_window.f32"), dtype="<f4").reshape(H, W)
    tr = from_origin(bb["west"], bb["north"], (bb["east"] - bb["west"]) / W, (bb["north"] - bb["south"]) / H)
    drain = features.rasterize([(line_ll, 1)], out_shape=(H, W), transform=tr, all_touched=True, dtype="uint8").astype(bool)
    flw = pyflwdir.from_dem(data=z.astype("float32"), nodata=-9999.0, transform=tr, latlon=True)
    hand = flw.hand(drain=drain, elevtn=z.astype("float32"))
    cols, rws = np.meshgrid(np.arange(W), np.arange(H))
    lon_c, lat_c = tr * (cols + 0.5, rws + 0.5)
    xu, yu = TO_UTM.transform(lon_c.ravel(), lat_c.ravel())
    pts = shapely.points(xu, yu)
    dist = shapely.distance(line, pts).reshape(H, W)
    s_cell = shapely.line_locate_point(line, pts).reshape(H, W)
    hand_ok = np.isfinite(hand) & (hand > -9000)
    print("HAND: %d of %d cells reach the river line along ANADEM flow paths" % (hand_ok.sum(), H * W), flush=True)
    dom = hand_ok & (hand <= HAND_MAX) & (dist <= LATERAL_MAX) & (s_cell >= s_start) & (s_cell <= s_station)
    lab, _ = ndimage.label(dom)
    keep = np.unique(lab[drain & dom])
    dom = np.isin(lab, keep[keep > 0])
    with rasterio.open(os.path.join(terr, "hand_anadem.tif"), "w", driver="GTiff", width=W, height=H, count=1,
                       dtype="float32", crs="EPSG:4326", transform=tr, nodata=-9999.0, compress="deflate") as f:
        f.write(np.where(hand_ok, hand, -9999.0).astype("float32"), 1)
    polys = [shape(g) for g, v in features.shapes(dom.astype("uint8"), mask=dom, transform=tr) if v == 1]
    dom_ll = unary_union(polys)
    dom_utm = shapely.ops.transform(lambda x, y, z=None: TO_UTM.transform(x, y), dom_ll).buffer(0).simplify(5)
    gpd.GeoDataFrame(geometry=[dom_utm], crs=EPSG).to_file(os.path.join(terr, "domain.gpkg"), driver="GPKG")
    print("domain: %.1f km2" % (dom_utm.area / 1e6), flush=True)

    # ---- 2. composite terrain, 5 m
    minx, miny, maxx, maxy = dom_utm.bounds
    x0, y0 = math.floor((minx - 50) / DX) * DX, math.floor((miny - 50) / DX) * DX
    x1, y1 = math.ceil((maxx + 50) / DX) * DX, math.ceil((maxy + 50) / DX) * DX
    W5, H5 = int(round((x1 - x0) / PIX)), int(round((y1 - y0) / PIX))
    tr5 = from_origin(x0, y1, PIX, PIX)
    comp = np.full((H5, W5), np.nan, dtype="float32")
    reproject(z.astype("float32"), comp, src_transform=tr, src_crs="EPSG:4326", dst_transform=tr5, dst_crs=f"EPSG:{EPSG}",
              resampling=Resampling.bilinear, src_nodata=-9999.0, dst_nodata=np.nan)
    chan_poly = line.buffer(WIDTH / 2.0, cap_style="flat")
    chan = features.rasterize([(chan_poly, 1)], out_shape=(H5, W5), transform=tr5, all_touched=False, dtype="uint8").astype(bool)
    cr, cc = np.nonzero(chan)
    cx, cy = tr5 * (cc + 0.5, cr + 0.5)
    s_ch = shapely.line_locate_point(line, shapely.points(cx, cy))
    comp[cr, cc] = np.interp(s_ch, s_prof, bed_prof)

    # buildings: OSM, plus Microsoft footprints not overlapping an OSM one
    wb, sb, eb, nb = TO_LL.transform_bounds(x0, y0, x1, y1)
    cache = os.path.join(ROOT, "web", ".cache", "buildings")
    osm, seen = [], set()
    # chunk files (osm_buildings_i_j) and block files (osm_buildings_block_i_j: 2 x 2 chunks fetched at once)
    for fn in sorted(glob.glob(os.path.join(cache, "osm_buildings_*.json"))):
        for e in json.load(open(fn, encoding="utf-8")).get("elements", []):
            key = "%s/%s" % (e.get("type"), e.get("id"))
            if key in seen:
                continue
            seen.add(key)
            b = e.get("bounds")
            if not b or b["maxlon"] < wb or b["minlon"] > eb or b["maxlat"] < sb or b["minlat"] > nb:
                continue
            if (e.get("tags") or {}).get("building", "no") == "no":
                continue
            rings = []
            if e["type"] == "way":
                rings = [[(p["lon"], p["lat"]) for p in e.get("geometry", []) if p]]
            else:
                rings = [[(p["lon"], p["lat"]) for p in m.get("geometry", []) if p] for m in e.get("members", [])
                         if m.get("type") == "way" and (m.get("role") or "outer") == "outer" and m.get("geometry")]
            for r in rings:
                if len(r) >= 4 and r[0] == r[-1]:
                    osm.append(shapely.Polygon(r))
    osm = [p if p.is_valid else p.buffer(0) for p in osm]
    ms = []
    for fn in sorted(glob.glob(os.path.join(cache, "ms_*.csv.gz"))):
        with gzip.open(fn, "rt", encoding="utf-8") as f:
            for ln in f:
                k = ln.find("[[[")
                if k < 0:
                    continue
                try:
                    lo, la = (float(v) for v in ln[k + 3:k + 60].split("]")[0].split(",")[:2])
                except ValueError:
                    continue
                if not (wb - 0.005 <= lo <= eb + 0.005 and sb - 0.005 <= la <= nb + 0.005):
                    continue
                g = shape(json.loads(ln)["geometry"])
                for p in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
                    ms.append(p)
    tree = shapely.STRtree(osm) if osm else None
    ms_keep = [p for p in ms if tree is None or len(tree.query(p, predicate="intersects")) == 0]
    blds = gpd.GeoSeries(osm + ms_keep, crs=4326).to_crs(EPSG)
    blds = blds[blds.intersects(box(x0, y0, x1, y1))]
    if not os.environ.get("FLOOD_DIAG"):  # footprints used, for the LISFLOOD-FP build (pipeline/flood_lisflood_build.py)
        gpd.GeoDataFrame({"source": ["osm"] * len([g for g in blds.index if g < len(osm)]) +
                          ["microsoft"] * len([g for g in blds.index if g >= len(osm)])},
                         geometry=blds.values, crs=EPSG).to_file(os.path.join(terr, "buildings.gpkg"), driver="GPKG")
    bmask = features.rasterize([(g, 1) for g in blds], out_shape=(H5, W5), transform=tr5, all_touched=False,
                               dtype="uint8").astype(bool) & ~chan
    if os.environ.get("FLOOD_DIAG") != "nobuildings" and os.environ.get("FLOOD_DIAG") != "confined":
        comp[bmask] += LIFT_BUILDINGS
    if os.environ.get("FLOOD_DIAG") == "confined":  # diagnostic only: everything but the channel raised 20 m
        comp[~chan] += 20.0
    comp_path = os.path.join(terr, "composite_5m%s.tif" % ("_" + os.environ["FLOOD_DIAG"] if os.environ.get("FLOOD_DIAG") else ""))
    with rasterio.open(comp_path, "w", driver="GTiff", width=W5, height=H5, count=1, dtype="float32",
                       crs=f"EPSG:{EPSG}", transform=tr5, nodata=-9999.0, compress="deflate", tiled=True) as f:
        f.write(np.where(np.isfinite(comp), comp, -9999.0).astype("float32"), 1)
    print("composite 5 m: %d x %d; channel pixels %d; buildings: %d OSM + %d Microsoft (of %d) -> %d pixels raised"
          % (W5, H5, chan.sum(), len(osm), len(ms_keep), len(ms), bmask.sum()), flush=True)

    # ---- 3. roughness, 5 m
    wmeta = json.load(open(os.path.join(RAW, "worldcover", "worldcover_flood_run1.json"), encoding="utf-8"))
    wc = np.fromfile(os.path.join(RAW, "worldcover", "worldcover_flood_run1.u8"), dtype="u1").reshape(wmeta["height"], wmeta["width"])
    wtr = from_origin(wmeta["west"], wmeta["north"], wmeta["pixel_deg"], wmeta["pixel_deg"])
    cls = np.zeros((H5, W5), dtype="uint8")
    reproject(wc, cls, src_transform=wtr, src_crs="EPSG:4326", dst_transform=tr5, dst_crs=f"EPSG:{EPSG}",
              resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
    man = np.full((H5, W5), 0.035, dtype="float32")
    for k, v in MANNING.items():
        man[cls == k] = v
    man[chan] = args.n
    man_path = os.path.join(terr, "manning_5m_n%.3f.tif" % args.n)
    with rasterio.open(man_path, "w", driver="GTiff", width=W5, height=H5, count=1, dtype="float32",
                       crs=f"EPSG:{EPSG}", transform=tr5, nodata=-9999.0, compress="deflate", tiled=True) as f:
        f.write(man, 1)

    # ---- 4. SFINCS model (HydroMT-SFINCS)
    from hydromt_sfincs import SfincsModel
    os.makedirs(out, exist_ok=True)
    mod = SfincsModel(root=out, mode="w+")
    mmax, nmax = int(round((x1 - x0) / DX)), int(round((y1 - y0) / DX))
    mod.grid.create(x0=x0, y0=y0, dx=DX, dy=DX, nmax=nmax, mmax=mmax, rotation=0, epsg=EPSG)
    mod.elevation.create(elevation_list=[{"elevation": comp_path}])
    dom_gdf = gpd.GeoDataFrame(geometry=[dom_utm], crs=EPSG)
    mod.mask.create_active(include_polygon=dom_gdf)
    # water-level boundary: the domain's edge cells inside a strip across the valley at the station,
    # from 75 m above it to 200 m below it along the river (first build used two offset circles, which
    # selected no cells: SFINCS ran with a closed outlet)
    c_st, c_up = line.interpolate(s_station), line.interpolate(s_station - 50.0)
    tx_, ty_ = c_st.x - c_up.x, c_st.y - c_up.y
    tn = math.hypot(tx_, ty_)
    tx_, ty_ = tx_ / tn, ty_ / tn
    nx_, ny_ = -ty_, tx_
    strip = shapely.Polygon([(c_st.x + a * tx_ + b * nx_, c_st.y + a * ty_ + b * ny_)
                             for a, b in ((-75, -LATERAL_MAX), (200, -LATERAL_MAX), (200, LATERAL_MAX), (-75, LATERAL_MAX))])
    mod.mask.create_boundary(btype="waterlevel", include_polygon=gpd.GeoDataFrame(geometry=[strip], crs=EPSG))
    mod.subgrid.create(elevation_list=[{"elevation": comp_path}], roughness_list=[{"manning": man_path}],
                       nr_subgrid_pixels=SUB, nr_levels=int(os.environ.get("FLOOD_NLEV", "10")),
                       weight_option=os.environ.get("FLOOD_WEIGHT", "min"))
    mod.write()
    print("model written:", out, flush=True)

    # ---- 5. forcing and outputs as plain text
    def pt(s):
        p = line.interpolate(s)
        return p.x, p.y
    src = [("upstream", pt(s_start + 50.0))]
    tribs = json.load(open(os.path.join(PROC, "flood_run1_tributaries.json"), encoding="utf-8"))["points"]
    for t in tribs:
        s_t = line.project(utm_point(t["lat"], t["lon"]))
        if s_t < s_station - 1.0:
            src.append(("trib_%gkm2" % t["area_km2"], pt(s_t)))
    q_up, level = 15.0, None
    i_end = np.searchsorted(s_prof, s_station)
    bed_station = float(np.interp(s_station, s_prof, bed_prof))
    depth15 = (q_up / 7.8) ** (1 / 1.1)       # SP Aguas' last low-flow rating at 3E-063: Q = 7.8 (h - 0.90)^1.1
    level = bed_station + depth15              # PROVISIONAL downstream level, steady test only
    bnd = [pt(s_station - 12.5)]
    obs = [("gauge_3E-063", pt(s_gauge)), ("km1", pt(s_gauge + 1000)), ("km3", pt(s_gauge + 3000)),
           ("km5", pt(s_gauge + 5000)), ("near_station", pt(s_station - 100))]
    gx, gy = pt(s_gauge)
    a, b = line.interpolate(s_gauge - 20), line.interpolate(s_gauge + 20)
    tx, ty = (b.x - a.x), (b.y - a.y)
    nrm = math.hypot(tx, ty)
    nx, ny = -ty / nrm, tx / nrm
    crs_line = [(gx + 7.3 - 1500 * nx, gy + 3.1 - 1500 * ny), (gx + 7.3 + 1500 * nx, gy + 3.1 + 1500 * ny)]  # offset off cell centres
    with open(os.path.join(out, "sfincs.src"), "w") as f:
        f.writelines("%.2f %.2f \"%s\"\n" % (x, y, n) for n, (x, y) in src)
    t_end = args.hours * 3600  # the floodplain takes days to fill at this flow (24 h and 72 h were not steady)
    with open(os.path.join(out, "sfincs.dis"), "w") as f:
        for t in (0, t_end):
            f.write("%d %s\n" % (t, " ".join("%.3f" % (q_up if n == "upstream" else 0.0) for n, _ in src)))
    with open(os.path.join(out, "sfincs.bnd"), "w") as f:
        f.writelines("%.2f %.2f\n" % p for p in bnd)
    with open(os.path.join(out, "sfincs.bzs"), "w") as f:
        f.write("0 %.3f\n%d %.3f\n" % (level, t_end, level))
    with open(os.path.join(out, "sfincs.obs"), "w") as f:
        f.writelines("%.2f %.2f \"%s\"\n" % (x, y, n) for n, (x, y) in obs)
    with open(os.path.join(out, "sfincs.crs"), "w") as f:
        f.write("gauge\n2 2\n%.2f %.2f\n%.2f %.2f\n" % (crs_line[0] + crs_line[1]))
    inp = os.path.join(out, "sfincs.inp")
    keep = [ln for ln in open(inp).read().splitlines() if ln.split("=")[0].strip() not in
            ("tref", "tstart", "tstop", "dtmapout", "dtout", "dthisout", "srcfile", "disfile", "bndfile", "bzsfile",
             "obsfile", "crsfile", "huthresh", "zsini", "outputformat", "storehsubgrid")]
    import datetime as dt
    stop = (dt.datetime(2000, 1, 1) + dt.timedelta(seconds=t_end)).strftime("%Y%m%d %H%M%S")
    extra = {"tref": "20000101 000000", "tstart": "20000101 000000", "tstop": stop, "dtmapout": 3600,
             "dthisout": 600, "srcfile": "sfincs.src", "disfile": "sfincs.dis", "bndfile": "sfincs.bnd",
             "bzsfile": "sfincs.bzs", "obsfile": "sfincs.obs", "crsfile": "sfincs.crs", "outputformat": "net",
             "storehsubgrid": 1}
    with open(inp, "w") as f:
        f.write("\n".join(keep) + "\n" + "".join("%-12s = %s\n" % kv for kv in extra.items()))
    summary = {"n_channel": args.n, "domain_km2": round(dom_utm.area / 1e6, 2), "grid": [mmax, nmax], "x0": x0, "y0": y0,
               "sources": [n for n, _ in src], "downstream_level_provisional_m": round(level, 3),
               "bed_at_station_m": round(bed_station, 2), "buildings": {"osm": len(osm), "microsoft_kept": len(ms_keep)}}
    json.dump(summary, open(os.path.join(out, "build_summary.json"), "w"), indent=1)
    print(json.dumps(summary), flush=True)
    if args.no_run:
        return

    # ---- steady test
    cmd = ["docker", "run", "--rm", "-v", out.replace("\\", "/") + ":/data", IMAGE]
    run = subprocess.run(cmd, capture_output=True, text=True)
    open(os.path.join(out, "docker_run.log"), "w", encoding="utf-8").write(run.stdout + "\n--- stderr ---\n" + run.stderr)
    print("\n".join(run.stdout.splitlines()[-14:]))
    if run.returncode != 0:
        print(run.stderr[-2000:])
        sys.exit("SFINCS exited with %d" % run.returncode)
    his = netCDF4.Dataset(os.path.join(out, "sfincs_his.nc"))
    t = np.asarray(his.variables["time"][:], dtype=float)
    zs = np.asarray(his.variables["point_zs"][:]).reshape(len(t), -1)
    last = t >= t[-1] - 7200
    ok = True
    for k, (n, _) in enumerate(obs):
        dz = float(np.nanmax(zs[last, k]) - np.nanmin(zs[last, k]))
        ok &= dz < 0.01
        print("%-14s level %.3f m (last 2 h change %.1f cm)" % (n, float(zs[-1, k]), 100 * dz))
    qn = next((v for v in ("crosssection_discharge", "cross_section_discharge") if v in his.variables), None)
    if qn:
        q = float(np.mean(np.abs(np.asarray(his.variables[qn][:]).reshape(len(t), -1)[last, 0])))
        print("discharge through the gauge cross-section: %.2f m3/s (inflow %.1f)" % (q, q_up))
        ok &= abs(q - q_up) / q_up < 0.05
    else:
        ok = False
    zg = float(zs[-1, 0])
    bank_g = float(np.interp(s_gauge, s_prof, bank_prof))
    print("at the gauge: modelled level %.2f m = %.2f m on the gauge scale (bank %.2f m = 3.01; SP Aguas' rating gives %.2f for 15 m3/s)"
          % (zg, zg - (bank_g - OVERFLOW_M), bank_g, H0_M + depth15))
    print("STEADY TEST", "PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
