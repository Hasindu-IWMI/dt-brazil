"""Observed flood maps from the evening Stripmap passes, for flood run 2 (docs/model_design_flood_run2.md).

Pre-run checks 4 and 6. The processing is the design's, fixed before any evening scene is read:
  1. calibrate to sigma-nought with each scene's calibration table;
  2. remove thermal noise with its noise table;
  3. terrain-correct with GLO-30 (ellipsoidal heights: GLO-30 + the EGM2008 geoid);
  4. flatten the radiometry to gamma-nought (sarsen's gamma terrain flattening);
  5. output on run 1's scoring grid (EPSG:32723, 10 m, 521 x 443).
The co-polarised channel only: HH on relative orbit 46 (21:35 UTC), VV on orbit 119 (21:43 UTC).

Subcommands:
  dem      the ellipsoidal DEM on the scoring grid: windows of the GLO-30 tile and of the EGM2008 geoid,
           read by byte range, logged in the manifest (models/flood_run2/radar/, not committed)
  check4   pre-run check 4 on DRY scenes only (one per orbit): geolocation against run 1's orbit-53
           sentinel-1-rtc dry median by cross-correlation (within 10 m), median gamma-nought on the scored
           ground within 2 dB of run 1's -7 to -9 dB, open water below -15 dB.
  maps     pre-run check 6 (written later): every scored pass and its references, the flood rule, the
           patch rule and the data gate.

The DEM step runs in either the atibaia-sfincs or the atibaia-sar environment (rasterio); check4 and maps
need atibaia-sar (sarsen). Usage: python pipeline/flood_sm_maps.py dem|check4|maps
"""
import hashlib
import json
import os
import sys

# conda on Windows: point GDAL and PROJ at the environment's own data (without them a reprojection can
# crash the process with no message)
for _k, _d in (("GDAL_DATA", "gdal"), ("PROJ_DATA", "proj")):
    _p = os.path.join(sys.prefix, "Library", "share", _d)
    if _k not in os.environ and os.path.isdir(_p):
        os.environ[_k] = _p

import numpy as np  # noqa: E402
import rasterio
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import from_bounds

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c  # noqa: E402

ROOT = c.ROOT
WORK = os.path.join(ROOT, "models", "flood_run2", "radar")
GRID_TIF = os.path.join(c.PROCESSED, "flood_run1_scoring_mask.tif")
GLO30 = ("https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_S24_00_W047_00_DEM/"
         "Copernicus_DSM_COG_10_S24_00_W047_00_DEM.tif")
GEOID = "https://cdn.proj.org/us_nga_egm08_25.tif"
DEM_TIF = os.path.join(WORK, "dem_ellipsoidal_scoring_grid.tif")
DEM_RES_TIF = os.path.join(WORK, "dem_ellipsoidal_reservoir_grid.tif")
RES_OSM_WAY = "way/31880069"
RES_BOX = (-46.646, -23.101, -46.628, -23.074)  # lon/lat around that pond
BLD_DENSITY = os.path.join(WORK, "building_density_scoring_grid.npy")  # made by `buildings` (atibaia-sfincs)

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "4")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "5")


def scoring_grid():
    with rasterio.open(GRID_TIF) as s:
        return {"transform": s.transform, "crs": s.crs, "width": s.width, "height": s.height, "mask": s.read(1) == 1}


def read_window_to_grid(url, grid, label, margin_deg=0.02):
    """A window of a remote raster (byte-range reads), bilinear onto the grid; logged in the manifest."""
    tr, W, H = grid["transform"], grid["width"], grid["height"]
    bounds = (tr.c, tr.f + H * tr.e, tr.c + W * tr.a, tr.f)
    out = np.full((H, W), np.nan, dtype="float32")
    with rasterio.open("/vsicurl/" + url) as src:
        b = transform_bounds(grid["crs"], src.crs, *bounds)
        b = (b[0] - margin_deg, b[1] - margin_deg, b[2] + margin_deg, b[3] + margin_deg)
        win = from_bounds(*b, src.transform).round_offsets().round_lengths()
        arr = src.read(1, window=win, boundless=True, fill_value=np.nan).astype("float32")
        reproject(arr, out, src_transform=src.window_transform(win), src_crs=src.crs, dst_transform=tr, dst_crs=grid["crs"],
                  resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
        c.append_manifest({"source": label, "url": url, "file": None, "window_lonlat": [round(v, 5) for v in b],
                           "window_px": [int(win.col_off), int(win.row_off), int(win.width), int(win.height)],
                           "sha256_values": hashlib.sha256(np.nan_to_num(arr, nan=-9999).tobytes()).hexdigest(),
                           "note": "window read by byte range for flood run 2 (values cached outside git)"})
    return out


def reservoir_grid():
    """A 10 m grid (EPSG:32723) over the Salto Grande plant's pond (OSM way 31880069), the nearest reservoir to
    the town, for the open-water test (no reservoir lies in the scoring grid)."""
    from rasterio.transform import from_origin
    from rasterio.warp import transform
    xs, ys = transform("EPSG:4326", "EPSG:32723", [RES_BOX[0], RES_BOX[2]], [RES_BOX[1], RES_BOX[3]])
    x0, x1 = 10 * np.floor(min(xs) / 10), 10 * np.ceil(max(xs) / 10)
    y0, y1 = 10 * np.floor(min(ys) / 10), 10 * np.ceil(max(ys) / 10)
    W, H = int((x1 - x0) / 10), int((y1 - y0) / 10)
    return {"transform": from_origin(x0, y1, 10, 10), "crs": rasterio.crs.CRS.from_epsg(32723), "width": W, "height": H,
            "mask": np.ones((H, W), bool)}


def make_dem(grid=None, path=DEM_TIF):
    grid = grid or scoring_grid()
    os.makedirs(WORK, exist_ok=True)
    h = read_window_to_grid(GLO30, grid, "Copernicus DEM GLO-30 (AWS copernicus-dem-30m), heights above EGM2008")
    # the geoid grid is 2.5' (about 4.6 km): a wider margin so that bilinear interpolation has neighbours
    n = read_window_to_grid(GEOID, grid, "EGM2008 geoid undulation, PROJ data CDN (us_nga_egm08_25.tif)", margin_deg=0.15)
    ell = (h + n).astype("float32")
    with rasterio.open(path, "w", driver="GTiff", width=grid["width"], height=grid["height"], count=1, dtype="float32",
                       crs=grid["crs"], transform=grid["transform"], nodata=np.nan) as dst:
        dst.write(ell, 1)
    rep = {"glo30_m": [round(float(np.nanmin(h)), 1), round(float(np.nanmax(h)), 1)],
           "geoid_m": [round(float(np.nanmin(n)), 2), round(float(np.nanmax(n)), 2)],
           "ellipsoidal_m": [round(float(np.nanmin(ell)), 1), round(float(np.nanmax(ell)), 1)], "nan_cells": int(np.isnan(ell).sum())}
    print("DEM on the scoring grid:", rep)
    return rep


# ---------------------------------------------------------------- Stripmap scenes (atibaia-sar)
TOKEN_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-1-grd"
SOURCE = "Sentinel-1 GRD Stripmap (Microsoft Planetary Computer, sentinel-1-grd; Copernicus Sentinel data, free and open)"
MARGIN_DEG = 0.03  # crop margin around the scoring grid, before terrain correction
MIN_LINEAR = 1e-4  # noise-subtracted power floor (-40 dB)
_tok = {"v": None, "t": 0.0}


def token():
    """Planetary Computer's read token for the collection (never written anywhere)."""
    import time
    import urllib.request
    if _tok["v"] is None or time.time() - _tok["t"] > 1800:
        req = urllib.request.Request(TOKEN_URL, headers={"User-Agent": c.USER_AGENT})
        _tok["v"] = json.load(urllib.request.urlopen(req, timeout=60))["token"]
        _tok["t"] = time.time()
    return _tok["v"]


def catalogue():
    import glob
    import gzip
    out = {}
    for p in glob.glob(os.path.join(c.RAW, "s1", "s1grd_sm_asc_*.json.gz")):
        for f in json.load(gzip.open(p, "rt", encoding="utf-8"))["features"]:
            out[f["id"]] = f
    return out


def noise_power(fs, path, lines, pixels):
    """ESA thermal noise power (DN^2) on the given lines x pixels: the range noise vectors (either
    annotation format: noiseRangeVector/noiseRangeLut from IPF 2.9, noiseVector/noiseLut before), times
    the azimuth noise vector where there is one."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(fs.cat(path))
    vecs, tag = root.findall(".//{*}noiseRangeVector"), "noiseRangeLut"
    if not vecs:
        vecs, tag = root.findall(".//{*}noiseVector"), "noiseLut"
    vl = np.array([int(v.find("{*}line").text) for v in vecs], float)
    per_vec = np.array([np.interp(pixels, np.array(v.find("{*}pixel").text.split(), float),
                                  np.array(v.find("{*}" + tag).text.split(), float)) for v in vecs])  # (vectors, pixels)
    rng = np.empty((len(lines), len(pixels)), dtype="float64")
    for j in range(len(pixels)):
        rng[:, j] = np.interp(lines, vl, per_vec[:, j])
    az = root.findall(".//{*}noiseAzimuthVector")
    if az:
        al = np.array(az[0].find("{*}line").text.split(), float)
        alut = np.array(az[0].find("{*}noiseAzimuthLut").text.split(), float)
        rng *= np.interp(lines, al, alut)[:, None]
    return rng


def open_scene(item, pol, grid, tag=""):
    """A sarsen product for one scene, cropped to the scoring grid plus a margin, calibrated to beta-nought
    with thermal noise removed. Returns (product, record for the manifest)."""
    import adlfs
    import attrs
    import sarsen
    import xarray as xr

    href = item["assets"]["safe-manifest"]["href"]
    account = href.split("//")[1].split(".")[0]
    fs = adlfs.AzureBlobFileSystem(account_name=account, sas_token=token())
    beam = item["id"].split("_")[1]
    group = "%s/%s" % (beam, pol.upper())
    blob = lambda key: item["assets"][key]["href"].split(".net/")[1]  # noqa: E731
    # Planetary Computer's file names, built from the folder: for newer products (with radio-interference
    # reports) the catalogue's "schema-product" entry points at annotation/rfi/rfi-*.xml, not the annotation
    folder_pc = blob("safe-manifest").rsplit("/", 1)[0]
    sp = "%s-%s" % (beam.lower(), pol.lower())
    pc_files = {"annotation": "%s/annotation/%s.xml" % (folder_pc, sp),
                "calibration": "%s/annotation/calibration/calibration-%s.xml" % (folder_pc, sp),
                "noise": "%s/annotation/calibration/noise-%s.xml" % (folder_pc, sp)}
    noise_path = pc_files["noise"]

    # the crop: the scene's tie points (latitude, longitude by line and pixel) around the grid
    tr, W, H = grid["transform"], grid["width"], grid["height"]
    b = transform_bounds(grid["crs"], "EPSG:4326", tr.c, tr.f + H * tr.e, tr.c + W * tr.a, tr.f)
    b = (b[0] - MARGIN_DEG, b[1] - MARGIN_DEG, b[2] + MARGIN_DEG, b[3] + MARGIN_DEG)
    # the geolocation grid of the product annotation (xarray-sentinel's reader finds no points in these
    # Stripmap files, so it is read here)
    import xml.etree.ElementTree as ET
    ann_bytes = fs.cat(pc_files["annotation"])
    ann = ET.fromstring(ann_bytes)
    pts = [(int(p.find("{*}line").text), int(p.find("{*}pixel").text), float(p.find("{*}latitude").text), float(p.find("{*}longitude").text))
           for p in ann.findall(".//{*}geolocationGridPoint")]
    if not pts:
        raise RuntimeError("no geolocation grid in the annotation of " + item["id"])
    li_all, pi_all, lat, lon = (np.array(v) for v in zip(*pts))
    inside = (lon >= b[0]) & (lon <= b[2]) & (lat >= b[1]) & (lat <= b[3])
    if not inside.any():  # tie points are sparse: take the nearest ones around the window
        near = np.hypot(lon - (b[0] + b[2]) / 2, lat - (b[1] + b[3]) / 2)
        inside = near <= np.sort(near)[min(8, near.size - 1)]
    li, pi = li_all[inside], pi_all[inside]
    # widen by one tie-point step, so the window lies wholly inside the crop
    dl = int(np.diff(np.unique(li_all)).max())
    dp = int(np.diff(np.unique(pi_all)).max())
    lines = (max(0, int(li.min()) - dl), int(li.max()) + dl)
    pixels = (max(0, int(pi.min()) - dp), int(pi.max()) + dp)

    # A minimal standard SAFE folder on disk, so that xarray-sentinel and sarsen read a normal product:
    # the manifest and this polarisation's three annotation files under ESA's own names, and the
    # measurement as a sparse tiled GeoTIFF of the full size holding only the window (the rest is never
    # read). Planetary Computer renames the files; the manifest gives the standard names.
    import re
    safe = os.path.join(WORK, "safe", item["id"] + tag + ".SAFE")
    done = os.path.join(safe, ".complete")
    if not os.path.exists(done):
        man = fs.cat(blob("safe-manifest"))
        names = re.findall(rb'href="\./([^"]+)"', man)
        tag = ("-%s-" % pol.lower()).encode()
        want = {"annotation": None, "calibration": None, "noise": None, "measurement": None}
        for n in names:
            n = n.decode()
            if ("-%s-" % pol.lower()) not in n:
                continue
            if n.startswith("annotation/calibration/calibration-"):
                want["calibration"] = n
            elif n.startswith("annotation/calibration/noise-"):
                want["noise"] = n
            elif n.startswith("annotation/") and n.count("/") == 1:
                want["annotation"] = n
            elif n.startswith("measurement/"):
                want["measurement"] = n
        if None in want.values():
            raise RuntimeError("manifest of %s lacks a %s file: %s" % (item["id"], pol, want))
        del tag
        os.makedirs(os.path.join(safe, "annotation", "calibration"), exist_ok=True)
        os.makedirs(os.path.join(safe, "measurement"), exist_ok=True)
        open(os.path.join(safe, "manifest.safe"), "wb").write(man)
        for key in ("annotation", "calibration", "noise"):
            open(os.path.join(safe, want[key]), "wb").write(ann_bytes if key == "annotation" else fs.cat(pc_files[key]))
        url = item["assets"][pol.lower()]["href"] + "?" + token()
        with rasterio.open(url) as src:
            prof = {"driver": "GTiff", "width": src.width, "height": src.height, "count": 1, "dtype": src.dtypes[0],
                    "tiled": True, "blockxsize": 512, "blockysize": 512, "compress": "deflate", "SPARSE_OK": True}
            win = rasterio.windows.Window(pixels[0], lines[0], min(pixels[1], src.width) - pixels[0], min(lines[1], src.height) - lines[0])
            arr = src.read(1, window=win)
        with rasterio.open(os.path.join(safe, want["measurement"]), "w", **prof) as dst:
            dst.write(arr, 1, window=win)
        open(done, "w").write("ok")
    kwargs = {"parse_geospatial_attrs": False}
    folder = safe
    import glob as _glob
    noise_path = _glob.glob(os.path.join(safe, "annotation", "calibration", "noise-*-%s-*.xml" % pol.lower()))[0]

    class _Local:  # noise_power reads through .cat()
        @staticmethod
        def cat(p):
            with open(p, "rb") as f:
                return f.read()

    local = _Local()

    def ns(ds):
        """Times as datetime64[ns], as sarsen 0.9 requires (this xarray keeps xarray-sentinel's microseconds)."""
        if ds is None:
            return ds
        for name in list(ds.coords) + list(getattr(ds, "data_vars", [])):
            v = ds[name]
            if np.issubdtype(v.dtype, np.datetime64) and v.dtype != np.dtype("datetime64[ns]"):
                ds = ds.assign_coords({name: v.astype("datetime64[ns]")}) if name in ds.coords else ds.assign({name: v.astype("datetime64[ns]")})
            elif np.issubdtype(v.dtype, np.timedelta64) and v.dtype != np.dtype("timedelta64[ns]"):
                ds = ds.assign_coords({name: v.astype("timedelta64[ns]")}) if name in ds.coords else ds.assign({name: v.astype("timedelta64[ns]")})
        return ds

    def parent(self, name):
        """sarsen's own property on the product (a property in 0.9.3, a cached_property in 0.9.6)."""
        attr = sarsen.Sentinel1SarProduct.__dict__[name]
        return (attr.fget if hasattr(attr, "fget") else attr.func)(self)

    @attrs.define(slots=False)
    class CroppedNoiseFree(sarsen.Sentinel1SarProduct):
        @property
        def measurement(self):
            ds = parent(self, "measurement")
            n_az, n_rg = ds.sizes["azimuth_time"], ds.sizes["ground_range"]
            return ns(ds.isel(azimuth_time=slice(lines[0], min(lines[1], n_az)), ground_range=slice(pixels[0], min(pixels[1], n_rg))))

        @property
        def orbit(self):
            return ns(parent(self, "orbit"))

        @property
        def calibration(self):
            return ns(parent(self, "calibration"))

        @property
        def coordinate_conversion(self):
            return ns(parent(self, "coordinate_conversion"))

        def beta_nought(self):
            m = self.measurement.data_vars["measurement"]
            dn = m.values.astype("float64")
            eta = noise_power(local, noise_path, m.line.values.astype(float), m.pixel.values.astype(float))
            lut = self.calibration.betaNought.interp(line=m.line, pixel=m.pixel).values.astype("float64")
            beta = np.maximum(dn * dn - eta, MIN_LINEAR * lut * lut) / (lut * lut)
            out = xr.DataArray(beta.astype("float32"), coords=m.coords, dims=m.dims, attrs=m.attrs)
            return out.drop_vars([v for v in ("pixel", "line") if v in out.coords])

    product = CroppedNoiseFree(product_urlpath=folder, measurement_group=group, measurement_chunks=None, kwargs=dict(kwargs))
    rec = {"source": SOURCE, "item": item["id"], "url": href.rsplit("/", 1)[0], "file": None, "group": group,
           "measurement_window_lines_pixels": [lines[0], lines[1], pixels[0], pixels[1]],
           "files_read": ["manifest.safe", "annotation (product, calibration, noise) for %s" % pol.upper(),
                          "measurement %s window" % pol.upper()],
           "note": "flood run 2 radar input (cached outside git); read with a short-lived access token, not recorded"}
    return product, rec


def gamma0_db(item_id, pol, grid, cat, dem=DEM_TIF, tag=""):
    """Terrain-corrected gamma-nought (dB) of one scene on a grid (the scoring grid unless given); cached as .npy."""
    import sarsen
    path = os.path.join(WORK, "%s_%s%s_gamma0_db.npy" % (item_id, pol.lower(), tag))
    if os.path.exists(path):
        return np.load(path)
    product, rec = open_scene(cat[item_id], pol, grid, tag)
    tif = os.path.join(WORK, "%s_%s%s_gtc.tif" % (item_id, pol.lower(), tag))
    g = sarsen.terrain_correction(product, dem_urlpath=dem, output_urlpath=tif, correct_radiometry="gamma_bilinear",
                                  interp_method="nearest", chunks=1024)
    # rows north first and columns west first, as the scoring grid (sarsen may return y ascending)
    g = g.sortby("y", ascending=False).sortby("x", ascending=True)
    a = np.asarray(g.values, dtype="float32")
    a = np.where(np.isfinite(a) & (a > 0), a, np.nan)
    db = (10.0 * np.log10(a)).astype("float32")
    if db.shape != (grid["height"], grid["width"]):
        raise RuntimeError("terrain-corrected scene is %s, expected the scoring grid" % (db.shape,))
    np.save(path, db)
    rec["sha256_values"] = hashlib.sha256(np.nan_to_num(db, nan=-999).tobytes()).hexdigest()
    c.append_manifest(rec)
    try:
        os.remove(tif)
    except OSError:
        pass
    return db


def run1_dry_median():
    """Run 1's orbit-53 sentinel-1-rtc VV dry median on the scoring grid, from its cached windows."""
    p = json.load(open(os.path.join(c.PROCESSED, "flood_run1_passes.json"), encoding="utf-8"))
    refs = {r["item"] for x in p["passes"] for r in x["references"]}
    cache = os.path.join(ROOT, "models", "flood_run1", "radar")
    arrs = [np.load(os.path.join(cache, f)) for f in sorted(os.listdir(cache)) if f.endswith("_vv_db.npy") and any(f.startswith(i) for i in refs)]
    return np.nanmedian(np.stack(arrs), axis=0), len(arrs)


def shift_m(a, b, max_px=5):
    """Offset (m) of a against b by cross-correlation of their local anomalies (5 x 5 mean removed),
    integer search +-max_px then a parabola through the peak."""
    from scipy.ndimage import uniform_filter

    def anomaly(x):
        x = np.where(np.isfinite(x), x, np.nanmedian(x))
        return x - uniform_filter(x, 5)

    A, B = anomaly(a), anomaly(b)
    H, W = A.shape
    m = max_px
    core = (slice(m, H - m), slice(m, W - m))
    score = np.full((2 * m + 1, 2 * m + 1), -1.0)
    for dy in range(-m, m + 1):
        for dx in range(-m, m + 1):
            sa = A[m + dy:H - m + dy, m + dx:W - m + dx]
            sb = B[core]
            score[dy + m, dx + m] = np.corrcoef(sa.ravel(), sb.ravel())[0, 1]
    iy, ix = np.unravel_index(np.argmax(score), score.shape)

    def para(v0, v1, v2):
        d = v0 - 2 * v1 + v2
        return 0.0 if d >= 0 else 0.5 * (v0 - v2) / d

    fy = iy - m + (para(score[iy - 1, ix], score[iy, ix], score[iy + 1, ix]) if 0 < iy < 2 * m else 0)
    fx = ix - m + (para(score[iy, ix - 1], score[iy, ix], score[iy, ix + 1]) if 0 < ix < 2 * m else 0)
    return 10.0 * fx, -10.0 * fy, float(score[iy, ix])


def worldcover_on_grid(grid):
    wm = json.load(open(os.path.join(c.RAW, "worldcover", "worldcover_flood_run1.json"), encoding="utf-8"))
    wc = np.fromfile(os.path.join(c.RAW, "worldcover", "worldcover_flood_run1.u8"), dtype="u1").reshape(wm["height"], wm["width"])
    out = np.zeros((grid["height"], grid["width"]), dtype="uint8")
    from rasterio.transform import from_origin
    reproject(wc, out, src_transform=from_origin(wm["west"], wm["north"], wm["pixel_deg"], wm["pixel_deg"]), src_crs="EPSG:4326",
              dst_transform=grid["transform"], dst_crs=grid["crs"], resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
    return out


def check4():
    """Pre-run check 4: one DRY scene from each evening orbit (the nearest dry reference of the first
    scored pass on that orbit). No flood scene is read."""
    grid = scoring_grid()
    cat = catalogue()
    passes = json.load(open(os.path.join(c.PROCESSED, "flood_run2_passes.json"), encoding="utf-8"))["passes"]
    ref53, n53 = run1_dry_median()
    wc = worldcover_on_grid(grid)
    # open water: no reservoir lies in the scoring grid, so the test uses its standing water instead:
    # WorldCover water cells that run 1's independent dry median (morning, VV) already reads below -15 dB
    water = (wc == 80) & (ref53 < -15.0)
    mask = grid["mask"]
    res = {"design": "docs/model_design_flood_run2.md", "check": "pre-run check 4", "run1_dry_median_scenes": n53,
           "run1_dry_median_db_on_mask": round(float(np.nanmedian(ref53[mask])), 2), "open_water_cells": int(water.sum()), "scenes": []}
    # the reservoir: the OSM pond on its own grid, 20 m in from the shore
    rgrid = reservoir_grid()
    if not os.path.exists(DEM_RES_TIF):
        make_dem(rgrid, DEM_RES_TIF)
    vec = json.load(open(os.path.join(ROOT, "web", "public", "data", "vectors.json"), encoding="utf-8"))
    ring = next(w for w in vec["waters"] if w["id"] == RES_OSM_WAY)["rings"][0]
    from rasterio import features
    from rasterio.warp import transform
    xs, ys = transform("EPSG:4326", "EPSG:32723", [p[0] for p in ring], [p[1] for p in ring])
    from scipy.ndimage import binary_erosion
    pond = features.rasterize([({"type": "Polygon", "coordinates": [list(zip(xs, ys))]}, 1)], out_shape=(rgrid["height"], rgrid["width"]),
                              transform=rgrid["transform"], dtype="uint8").astype(bool)
    pond_core = binary_erosion(pond, iterations=2)
    res["reservoir"] = {"osm": RES_OSM_WAY, "cells": int(pond.sum()), "interior_cells": int(pond_core.sum())}
    bld = np.load(BLD_DENSITY) if os.path.exists(BLD_DENSITY) else None
    for orbit in (46, 119):
        p = next(x for x in passes if x["scored"] and x["orbit"] == orbit)
        pol = "hh" if "HH" in p["pols"] else "vv"
        rid = p["references"][0]["item"]
        db = gamma0_db(rid, pol, grid, cat)
        dbr = gamma0_db(rid, pol, rgrid, cat, DEM_RES_TIF, "_reservoir")
        east, north, corr = shift_m(db, ref53)
        r = {"orbit": orbit, "polarisation": pol.upper(), "scene": rid, "stage_cm": p["references"][0]["stage_cm"],
             "valid_cells": int(np.isfinite(db).sum()), "median_db_on_mask": round(float(np.nanmedian(db[mask])), 2),
             "open_water_median_db": round(float(np.nanmedian(db[water])), 2) if water.any() else None,
             "reservoir_interior_median_db": round(float(np.nanmedian(dbr[pond_core])), 2),
             "reservoir_share_below_-15db": round(float(np.mean(dbr[pond_core] < -15)), 3),
             "shift_east_m": round(east, 1), "shift_north_m": round(north, 1), "shift_m": round(float(np.hypot(east, north)), 1),
             "peak_correlation": round(corr, 3)}
        if bld is not None:  # geolocation against the mapped buildings (optical geometry): bright radar where buildings are
            from scipy.ndimage import gaussian_filter
            e2, n2, c2 = shift_m(gaussian_filter(np.where(np.isfinite(db), db, np.nanmedian(db)), 1.0), gaussian_filter(bld, 1.0), max_px=12)
            r.update({"shift_vs_buildings_east_m": round(e2, 1), "shift_vs_buildings_north_m": round(n2, 1),
                      "shift_vs_buildings_m": round(float(np.hypot(e2, n2)), 1), "buildings_correlation": round(c2, 3)})
        r["passed_as_written"] = bool(r["shift_m"] <= 10.0 and -11.0 <= r["median_db_on_mask"] <= -5.0
                                      and r["reservoir_interior_median_db"] < -15.0)
        r["passed"] = r["passed_as_written"]
        res["scenes"].append(r)
        print(json.dumps(r), flush=True)
    res["passed"] = all(s["passed"] for s in res["scenes"])
    with open(os.path.join(c.PROCESSED, "flood_run2_check4.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print("CHECK 4", "PASSED" if res["passed"] else "FAILED (fix the processing, or fall back to SNAP, before any flood scene is read)")

# ---------------------------------------------------------------- check 6: the observed maps and the gate
DROP_DB, MAX_DB, PATCH_MIN, MIN_PIXELS, GATE_PASSES, GATE_RHO = 3.0, -15.0, 4, 1000, 4, 0.5


def _gamma0_job(args):
    """Worker: one scene on the scoring grid (separate process; returns the cache path or an error)."""
    item_id, pol = args
    try:
        gamma0_db(item_id, pol, scoring_grid(), catalogue())
        return item_id, pol, None
    except Exception as e:  # noqa: BLE001
        return item_id, pol, "%s: %s" % (type(e).__name__, str(e)[:300])


def permanent_water(grid):
    """Mapped permanent water on the scoring grid: WorldCover 80 and 90, and OSM water polygons."""
    from rasterio import features
    from rasterio.warp import transform
    wc = worldcover_on_grid(grid)
    out = (wc == 80) | (wc == 90)
    vec = json.load(open(os.path.join(ROOT, "web", "public", "data", "vectors.json"), encoding="utf-8"))
    shapes = []
    for w in vec["waters"]:
        for ring in w["rings"]:
            if len(ring) >= 4:
                xs, ys = transform("EPSG:4326", "EPSG:32723", [q[0] for q in ring], [q[1] for q in ring])
                shapes.append(({"type": "Polygon", "coordinates": [list(zip(xs, ys))]}, 1))
    if shapes:
        out |= features.rasterize(shapes, out_shape=(grid["height"], grid["width"]), transform=grid["transform"], dtype="uint8").astype(bool)
    return out


def maps(workers=4):
    """Pre-run check 6: every scored pass and its references, the flood and patch rules, the data gate."""
    from scipy import ndimage, stats
    grid = scoring_grid()
    passes = [x for x in json.load(open(os.path.join(c.PROCESSED, "flood_run2_passes.json"), encoding="utf-8"))["passes"] if x["scored"]]
    jobs = []
    for x in passes:
        pol = "hh" if "HH" in x["pols"] else "vv"
        for i in [x["item"]] + [r["item"] for r in x["references"]]:
            if (i, pol) not in jobs:
                jobs.append((i, pol))
    todo = [j for j in jobs if not os.path.exists(os.path.join(WORK, "%s_%s_gamma0_db.npy" % j))]
    print("scenes: %d in all, %d to process" % (len(jobs), len(todo)), flush=True)
    errors = {}
    # a pool that is terminated once its results are in: GDAL's HTTP reader can keep a Windows worker alive
    import multiprocessing as mp
    pool = mp.Pool(workers)
    try:
        for k, (i, pol, err) in enumerate(pool.imap_unordered(_gamma0_job, todo), 1):
            if err:
                errors[i] = err
            if k % 10 == 0 or err:
                print("  %d/%d%s" % (k, len(todo), " ERROR %s %s" % (i, err) if err else ""), flush=True)
    finally:
        pool.terminate()
    perm = permanent_water(grid)
    mask = grid["mask"] & ~perm
    load = lambda i, pol: np.load(os.path.join(WORK, "%s_%s_gamma0_db.npy" % (i, pol)))  # noqa: E731
    out, bands, recs = [], [], []
    for x in passes:
        pol = "hh" if "HH" in x["pols"] else "vv"
        rec = {"pass": x["pass"], "item": x["item"], "orbit": x["orbit"], "polarisation": pol.upper(), "stage_cm": x["stage_cm"]}
        refs = [r["item"] for r in x["references"] if r["item"] not in errors]
        if x["item"] in errors or len(refs) < 3:
            rec.update({"radar_data": False, "why": "scene error" if x["item"] in errors else "fewer than 3 references processed"})
            recs.append(rec)
            bands.append(np.full((grid["height"], grid["width"]), 255, "uint8"))
            continue
        db = load(x["item"], pol)
        ref = np.nanmedian(np.stack([load(i, pol) for i in refs]), axis=0)
        valid = np.isfinite(db) & np.isfinite(ref)
        flood = valid & (db <= ref - DROP_DB) & (db < MAX_DB)
        lab, n = ndimage.label(flood)  # 4-connected by default
        sizes = ndimage.sum(flood, lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.nonzero(sizes >= PATCH_MIN)[0])
        n_mask = int((keep & mask).sum())
        rec.update({"radar_data": True, "references_used": len(refs), "flagged_before_patch_rule_on_mask": int((flood & mask).sum()),
                    "flooded_pixels_on_mask": n_mask, "flooded_km2_on_mask": round(n_mask * 100 / 1e6, 4),
                    "scored": n_mask >= MIN_PIXELS, "valid_on_mask": int((valid & mask).sum())})
        recs.append(rec)
        b = np.where(valid, 0, 255).astype("uint8")
        b[keep & grid["mask"]] = 1
        b[~grid["mask"] & (b != 255)] = 0
        bands.append(b)
    with_data = [r for r in recs if r["radar_data"]]
    g1 = sum(r["scored"] for r in with_data)
    rho = float(stats.spearmanr([r["stage_cm"] for r in with_data], [r["flooded_pixels_on_mask"] for r in with_data]).statistic) if len(with_data) >= 3 else float("nan")
    gate = {"G1_passes_at_or_over_1000_pixels": g1, "G1_needed": GATE_PASSES, "G1_passed": g1 >= GATE_PASSES,
            "G2_spearman_stage_vs_flooded": round(rho, 3), "G2_needed": GATE_RHO, "G2_passed": bool(np.isfinite(rho) and rho >= GATE_RHO)}
    gate["passed"] = gate["G1_passed"] and gate["G2_passed"]
    res = {"design": "docs/model_design_flood_run2.md", "check": "pre-run check 6", "built": __import__("datetime").date.today().isoformat(),
           "rule": {"drop_db": DROP_DB, "max_db": MAX_DB, "patch_min_pixels_4_connected": PATCH_MIN, "min_pixels_to_score": MIN_PIXELS},
           "scoring_mask_cells": int(mask.sum()), "permanent_water_removed_from_mask": int((grid["mask"] & perm).sum()),
           "scene_errors": errors, "gate": gate, "passes": recs}
    with open(os.path.join(c.PROCESSED, "flood_run2_observed.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    with rasterio.open(os.path.join(c.PROCESSED, "flood_run2_observed.tif"), "w", driver="GTiff", width=grid["width"], height=grid["height"],
                       count=len(bands), dtype="uint8", crs=grid["crs"], transform=grid["transform"], nodata=255, compress="deflate") as dst:
        for k, b in enumerate(bands, 1):
            dst.write(b, k)
            dst.set_band_description(k, recs[k - 1]["pass"])
    figure(grid, mask, bands, recs)
    print(json.dumps(gate))
    print("CHECK 6: data gate", "PASSED" if gate["passed"] else "FAILED (run 2 ends: no extent test, nothing modelled shown)")


def figure(grid, mask, bands, recs):
    """docs/flood_run2_observed.png: one panel per pass, flooded pixels (patch rule) in blue, the scoring
    mask's outline in grey, labelled with the pass, the stage and the flooded area on the mask."""
    from PIL import Image, ImageDraw
    from scipy import ndimage
    H, W = mask.shape
    s = 0.5
    h, w = int(H * s), int(W * s)
    cols = 5
    rows = (len(bands) + cols - 1) // cols
    pad = 22
    img = Image.new("RGB", (cols * (w + 6) + 6, rows * (h + pad + 6) + 6), (250, 250, 248))
    edge = mask & ~ndimage.binary_erosion(mask)
    for k, (b, r) in enumerate(zip(bands, recs)):
        rgb = np.full((H, W, 3), 236, "uint8")
        rgb[mask] = (214, 214, 208)
        rgb[b == 255] = (255, 255, 255)
        rgb[edge] = (120, 120, 116)
        rgb[b == 1] = (24, 96, 200)
        tile = Image.fromarray(rgb).resize((w, h), Image.NEAREST)
        x0, y0 = 6 + (k % cols) * (w + 6), 6 + (k // cols) * (h + pad + 6)
        img.paste(tile, (x0, y0 + pad))
        d = ImageDraw.Draw(img)
        label = "%s %s %s cm" % (r["pass"][:16].replace("T", " "), r["polarisation"], round(r["stage_cm"]))
        label2 = ("%.3f km2" % r["flooded_km2_on_mask"]) if r.get("radar_data") else "no radar data"
        d.text((x0, y0), label, fill=(20, 20, 20))
        d.text((x0, y0 + 11), label2 + ("" if r.get("scored") else "  (too small to score)" if r.get("radar_data") else ""), fill=(60, 60, 60))
    img.save(os.path.join(ROOT, "docs", "flood_run2_observed.png"))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dem":
        make_dem()
    elif cmd == "check4":
        check4()
    elif cmd == "maps":
        maps(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif cmd == "buildings":  # atibaia-sfincs (geopandas): building cover per scoring-grid cell, from run 1's footprints
        import geopandas as gpd
        from rasterio import features
        from rasterio.transform import Affine
        grid = scoring_grid()
        bl = gpd.read_file(os.path.join(ROOT, "models", "flood_run1", "terrain", "buildings.gpkg")).to_crs(grid["crs"])
        tr = grid["transform"]
        r5 = features.rasterize([(g, 1) for g in bl.geometry], out_shape=(grid["height"] * 5, grid["width"] * 5),
                                transform=Affine(tr.a / 5, 0, tr.c, 0, tr.e / 5, tr.f), dtype="uint8")
        os.makedirs(WORK, exist_ok=True)
        np.save(BLD_DENSITY, r5.reshape(grid["height"], 5, grid["width"], 5).mean(axis=(1, 3)).astype("float32"))
        print("building cover on the scoring grid:", len(bl), "footprints")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
    # GDAL's HTTP reader can keep a Windows process alive after the work is done and written: leave now
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
