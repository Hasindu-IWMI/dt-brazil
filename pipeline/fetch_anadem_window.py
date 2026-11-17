"""Read a window of ANADEM (bare-earth terrain, 30 m) around Atibaia town.

Pre-run check 1 of docs/model_design_flood_run1.md. ANADEM v1 (Laipelt et al.
2024, Remote Sensing 16(13):2321, doi:10.3390/rs16132321; ANA and UFRGS) is
served per MGRS grid zone as one GeoTIFF; Atibaia lies in zone 23K, a 2.05 GB
file. The file is tiled internally (512 x 512, deflate, float32, EPSG:4326)
and the server honours HTTP Range requests, so only the tiles that cover the
window are read: a few MB, not the whole file.

Stored:
  data/raw/dem/anadem_window.f32   float32 little-endian, rows north to south
  data/raw/dem/anadem_window.json  grid, source, file size, ETag, and per tile
                                   its byte range and SHA-256 of the bytes read
Each tile read is logged in data/raw/manifest.jsonl (URL, byte range, SHA-256).
The window is fixed below; rerunning rereads it only with --force.

Usage: python fetch_anadem_window.py [--force]
"""
import array
import json
import math
import os
import struct
import sys
import urllib.request
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

URL = "https://metadados.snirh.gov.br/files/anadem_v1_tiles/anadem_v1_23K.tif"
SOURCE = "ANADEM v1 (ANA / UFRGS), zone 23K, via https://www.ufrgs.br/hge/download-anadem/"
# Atibaia town reach with margin: the flood run 1 domain and the drainage needed around it
WEST, EAST, SOUTH, NORTH = -46.70, -46.48, -23.18, -23.03
OUT = os.path.join(c.RAW, "dem", "anadem_window")
TYPES = {1: ("B", 1), 2: ("c", 1), 3: ("H", 2), 4: ("I", 4), 12: ("d", 8), 16: ("Q", 8)}


def get_range(start, length):
    req = urllib.request.Request(URL, headers={"User-Agent": c.USER_AGENT,
                                               "Range": "bytes=%d-%d" % (start, start + length - 1)})
    with urllib.request.urlopen(req, timeout=120) as r:
        if r.status != 206:
            raise SystemExit("server did not honour the Range request (status %d)" % r.status)
        data = r.read()
    if len(data) != length:
        raise SystemExit("short read at %d: %d of %d bytes" % (start, len(data), length))
    return data


def main():
    if os.path.exists(OUT + ".f32") and "--force" not in sys.argv[1:]:
        print("already on disk:", os.path.relpath(OUT + ".f32", c.ROOT))
        return
    req = urllib.request.Request(URL, method="HEAD", headers={"User-Agent": c.USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        size, etag, modified = int(r.headers["Content-Length"]), r.headers.get("ETag"), r.headers.get("Last-Modified")

    head = get_range(0, 65536)
    if head[:4] != b"II*\x00":
        raise SystemExit("expected a little-endian classic TIFF")
    ifd = struct.unpack("<I", head[4:8])[0]
    n = struct.unpack("<H", head[ifd:ifd + 2])[0]
    tags = {}
    for k in range(n):
        tag, typ, cnt, raw = struct.unpack("<HHI4s", head[ifd + 2 + 12 * k: ifd + 14 + 12 * k])
        fmt, sz = TYPES[typ]
        if cnt * sz <= 4:
            vals = struct.unpack("<" + fmt * cnt, raw[:cnt * sz])
        else:
            off = struct.unpack("<I", raw)[0]
            blob = head[off:off + cnt * sz] if off + cnt * sz <= len(head) else get_range(off, cnt * sz)
            vals = struct.unpack("<" + fmt * cnt, blob)
        tags[tag] = vals
    width, height = tags[256][0], tags[257][0]
    tw, th = tags[322][0], tags[323][0]
    assert tags[259][0] == 8 and tags[339][0] == 3 and tags[258][0] == 32, "expected deflate float32"
    assert tags.get(317, (1,))[0] == 1, "expected no predictor"
    res = tags[33550][0]
    lon0, lat0 = tags[33922][3], tags[33922][4]
    nodata = float(b"".join(tags[42113]).rstrip(b"\x00").decode()) if 42113 in tags else None
    offsets, counts = tags[324], tags[325]
    tiles_across = math.ceil(width / tw)

    c0, c1 = int((WEST - lon0) / res), int(math.ceil((EAST - lon0) / res))
    r0, r1 = int((lat0 - NORTH) / res), int(math.ceil((lat0 - SOUTH) / res))
    W, H = c1 - c0, r1 - r0
    out = array.array("f", [float("nan")]) * (W * H)
    tiles = []
    for ty in range(r0 // th, (r1 - 1) // th + 1):
        for tx in range(c0 // tw, (c1 - 1) // tw + 1):
            k = ty * tiles_across + tx
            raw = get_range(offsets[k], counts[k])
            sha = c.sha256(raw)
            c.append_manifest({"source": SOURCE, "url": URL, "file": None, "range": [offsets[k], offsets[k] + counts[k] - 1],
                               "bytes": counts[k], "sha256": sha, "tile": [tx, ty], "note": "tile read for anadem_window"})
            tiles.append({"tile": [tx, ty], "offset": offsets[k], "bytes": counts[k], "sha256": sha})
            vals = array.array("f")
            vals.frombytes(zlib.decompress(raw))
            for rr in range(max(r0, ty * th), min(r1, (ty + 1) * th)):
                for cc in range(max(c0, tx * tw), min(c1, (tx + 1) * tw)):
                    v = vals[(rr - ty * th) * tw + (cc - tx * tw)]
                    out[(rr - r0) * W + (cc - c0)] = float("nan") if nodata is not None and v == nodata else v
            print("tile", tx, ty, counts[k], "bytes", flush=True)

    c.ensure_dir(os.path.dirname(OUT))
    with open(OUT + ".f32", "wb") as f:
        out.tofile(f)
    good = [v for v in out if v == v]
    meta = {"source": SOURCE, "url": URL, "file_bytes": size, "etag": etag, "last_modified": modified,
            "kind": "digital TERRAIN model (vegetation bias removed from Copernicus GLO-30)", "crs": "EPSG:4326",
            "verticalDatum": "as ANADEM v1 (EGM2008, from Copernicus GLO-30)", "units": "m",
            "pixel_deg": res, "width": W, "height": H, "rowOrder": "north to south", "dtype": "float32 little-endian",
            "bbox": {"west": lon0 + c0 * res, "east": lon0 + c1 * res, "north": lat0 - r0 * res, "south": lat0 - r1 * res},
            "requested": {"west": WEST, "east": EAST, "south": SOUTH, "north": NORTH},
            "nodata_cells": W * H - len(good), "min_m": min(good), "max_m": max(good), "tiles": tiles}
    with open(OUT + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    print("window %d x %d, %.1f to %.1f m, %d nodata; tiles read: %d (%.1f MB)" % (
        W, H, meta["min_m"], meta["max_m"], meta["nodata_cells"], len(tiles), sum(t["bytes"] for t in tiles) / 1e6))


if __name__ == "__main__":
    main()
