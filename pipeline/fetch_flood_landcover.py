"""ESA WorldCover classes around Atibaia town, for the roughness of flood run 1.

docs/model_design_flood_run1.md fixes floodplain roughness by WorldCover 2021
class. The viewer's tool (web/tools/build_landcover.mjs) reads the same COG
for display; this script reads only the window around the flood-run reach,
at the native 10 m, over HTTP Range requests (pipeline/cogread.py), and logs
every tile read in the manifest.

Stored: data/raw/worldcover/worldcover_flood_run1.u8 (class codes, rows north
to south) and .json (grid, source, tiles).

Usage: python fetch_flood_landcover.py
"""
import array
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
from cogread import read_window  # noqa: E402

URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_S24W048_Map.tif"
SOURCE = "ESA WorldCover 10 m 2021 v200 (CC BY 4.0)"
WEST, EAST, SOUTH, NORTH = -46.66, -46.50, -23.16, -23.04
OUT = os.path.join(c.RAW, "worldcover", "worldcover_flood_run1")


def main():
    if os.path.exists(OUT + ".u8"):
        print("already on disk:", os.path.relpath(OUT + ".u8", c.ROOT))
        return
    vals, w, h, grid = read_window(URL, WEST, SOUTH, EAST, NORTH, SOURCE, note="WorldCover window for flood run 1")
    arr = array.array("B", vals)
    c.ensure_dir(os.path.dirname(OUT))
    with open(OUT + ".u8", "wb") as f:
        arr.tofile(f)
    counts = {}
    for v in arr:
        counts[v] = counts.get(v, 0) + 1
    meta = {"source": SOURCE, "url": URL, "crs": "EPSG:4326", "width": w, "height": h, "rowOrder": "north to south",
            "west": grid["x0"], "north": grid["y0"], "pixel_deg": grid["res_x"], "tiles": grid["tiles"],
            "class_counts": dict(sorted(counts.items())), "sha256_window": c.sha256(arr.tobytes()),
            "attribution": "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) "
                           "processed by ESA WorldCover consortium"}
    with open(OUT + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    print("window %d x %d, tiles %d, classes %s" % (w, h, len(grid["tiles"]), meta["class_counts"]))


if __name__ == "__main__":
    main()
