"""Read a window of a tiled GeoTIFF over HTTP Range requests (standard library only).

Handles what the open sources used by flood run 1 serve: little-endian classic
TIFF, internally tiled, deflate (8) or no compression (1), predictor 1 or 2,
one band of uint8, uint16 or float32. Every tile read is logged in the
manifest with its URL, byte range and SHA-256.

Also: WGS84 latitude/longitude to UTM (south zones), for files in UTM.
"""
import array
import math
import struct
import urllib.request
import zlib

import common as c

TYPES = {1: ("B", 1), 2: ("c", 1), 3: ("H", 2), 4: ("I", 4), 12: ("d", 8), 16: ("Q", 8)}


def _range(url, start, length):
    req = urllib.request.Request(url, headers={"User-Agent": c.USER_AGENT,
                                               "Range": "bytes=%d-%d" % (start, start + length - 1)})
    last = None
    for _ in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                if r.status != 206:
                    raise SystemExit("server did not honour the Range request for %s" % url)
                data = r.read()
            if len(data) == length:
                return data
            last = IOError("short read %d of %d" % (len(data), length))
        except (OSError, urllib.error.URLError) as e:
            last = e
    raise last


def header(url):
    """Tags of the first image (full resolution) and the grid it defines."""
    head = _range(url, 0, 65536)
    if head[:4] != b"II*\x00":
        raise SystemExit("expected a little-endian classic TIFF: %s" % url)
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
            blob = head[off:off + cnt * sz] if off + cnt * sz <= len(head) else _range(url, off, cnt * sz)
            vals = struct.unpack("<" + fmt * cnt, blob)
        tags[tag] = vals
    return tags


def read_window(url, x0, y0, x1, y1, source, note=""):
    """Pixels covering [x0, x1] x [y0, y1] in the file's own CRS units.

    Returns (values as a flat list, width, height, grid) where grid has the
    window's top-left corner, pixel size and the tiles read (for provenance)."""
    t = header(url)
    W, H = t[256][0], t[257][0]
    tw, th = t[322][0], t[323][0]
    comp, pred = t[259][0], t.get(317, (1,))[0]
    bits, fmt = t[258][0], t.get(339, (1,))[0]
    code = {(8, 1): "B", (16, 1): "H", (32, 3): "f"}[(bits, fmt)]
    res_x, res_y = t[33550][0], t[33550][1]
    ox, oy = t[33922][3], t[33922][4]
    c0, c1 = max(0, int((x0 - ox) // res_x)), min(W, int(math.ceil((x1 - ox) / res_x)))
    r0, r1 = max(0, int((oy - y1) // res_y)), min(H, int(math.ceil((oy - y0) / res_y)))
    w, h = c1 - c0, r1 - r0
    out = [0] * (w * h)
    across = math.ceil(W / tw)
    tiles = []
    for ty in range(r0 // th, (r1 - 1) // th + 1):
        for tx in range(c0 // tw, (c1 - 1) // tw + 1):
            k = ty * across + tx
            raw = _range(url, t[324][k], t[325][k])
            sha = c.sha256(raw)
            c.append_manifest({"source": source, "url": url, "file": None, "range": [t[324][k], t[324][k] + t[325][k] - 1],
                               "bytes": t[325][k], "sha256": sha, "tile": [tx, ty], "note": note})
            tiles.append({"tile": [tx, ty], "bytes": t[325][k], "sha256": sha})
            data = zlib.decompress(raw) if comp == 8 else raw
            vals = array.array(code)
            vals.frombytes(data[:tw * th * vals.itemsize])
            if pred == 2:  # horizontal differencing, per row within the tile
                mod = 1 << bits
                for row in range(th):
                    base = row * tw
                    acc = vals[base]
                    for col in range(1, tw):
                        acc = (acc + vals[base + col]) % mod
                        vals[base + col] = acc
            for rr in range(max(r0, ty * th), min(r1, (ty + 1) * th)):
                src = (rr - ty * th) * tw
                for cc in range(max(c0, tx * tw), min(c1, (tx + 1) * tw)):
                    out[(rr - r0) * w + (cc - c0)] = vals[src + cc - tx * tw]
    grid = {"x0": ox + c0 * res_x, "y0": oy - r0 * res_y, "res_x": res_x, "res_y": res_y, "tiles": tiles}
    return out, w, h, grid


def utm_south(lat, lon, zone):
    """WGS84 latitude/longitude (degrees) to UTM easting/northing (m) in a southern zone."""
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    phi, lam = math.radians(lat), math.radians(lon)
    lam0 = math.radians(-183 + 6 * zone)
    N = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    T, C = math.tan(phi) ** 2, ep2 * math.cos(phi) ** 2
    A = math.cos(phi) * (lam - lam0)
    M = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi
             - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi)
             - (35 * e2 ** 3 / 3072) * math.sin(6 * phi))
    x = k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T * T + 72 * C - 58 * ep2) * A ** 5 / 120) + 500000.0
    y = k0 * (M + N * math.tan(phi) * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * A ** 4 / 24
                                        + (61 - 58 * T + T * T + 600 * C - 330 * ep2) * A ** 6 / 720)) + 10000000.0
    return x, y
