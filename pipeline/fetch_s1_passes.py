"""Catalogue entries for the Sentinel-1 passes of flood run 1 (docs/model_design_flood_run1.md).

Pre-run check 3, first half: confirm that every scored pass exists in
Microsoft Planetary Computer's `sentinel-1-rtc` collection (terrain-corrected
backscatter, 10 m, CC BY 4.0), and list the candidate dry-reference passes:
everything in the collection over Atibaia town within 60 days either side of
each scored pass. flood_passes.py then keeps those of the same relative orbit
taken while 3E-063 stood below 240 cm.

Only catalogue metadata (STAC JSON) is fetched here. No image is downloaded:
the design keeps the radar maps unseen until the mapping rule is applied to
all passes at once.

Raw responses are stored gzip-compressed in data/raw/s1/ and logged in the
manifest. Resumable: passes already on disk are skipped.

Not part of run_all.py: it serves one fixed experiment.

Usage: python fetch_s1_passes.py
"""
import datetime as dt
import gzip
import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402

API = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SOURCE = "Microsoft Planetary Computer STAC API, collection sentinel-1-rtc"
RAW_DIR = os.path.join(c.RAW, "s1")
BBOX = (-46.62, -23.16, -46.50, -23.06)  # Atibaia town reach, as searched in docs/flood_option_check.md
WINDOW_DAYS = 60

# The 17 scored passes, as fixed in the design (UTC, minute precision)
PASSES = ["2016-01-20T08:30", "2016-02-25T08:30", "2017-01-14T08:30", "2017-01-26T08:30",
          "2018-02-02T08:30", "2018-03-04T08:30", "2019-03-05T08:31", "2020-02-28T08:31",
          "2021-01-17T08:31", "2023-10-10T08:31", "2024-12-27T08:31", "2026-02-02T08:30",
          "2026-02-14T08:30", "2026-02-26T08:30", "2026-03-15T08:38", "2026-03-16T08:31",
          "2026-09-13T08:30"]


def main():
    for p in PASSES:
        name = "s1rtc_%s.json.gz" % p[:10]
        path = os.path.join(RAW_DIR, name)
        if os.path.exists(path):
            continue
        t = dt.datetime.fromisoformat(p)
        a = (t - dt.timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
        b = (t + dt.timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%dT23:59:59Z")
        params = {"collections": "sentinel-1-rtc", "bbox": ",".join(str(v) for v in BBOX),
                  "datetime": "%s/%s" % (a, b), "limit": 250}
        url = API + "?" + urllib.parse.urlencode(params)
        try:
            data = c.http_get(url, timeout=120, retries=4, backoff=15)
        except Exception as e:  # keep going; a re-run picks it up
            print("FAIL", p, e, flush=True)
            continue
        d = json.loads(data.decode("utf-8"))
        n = len(d.get("features") or [])
        more = any(l.get("rel") == "next" for l in d.get("links") or [])
        c.write_bytes(path, gzip.compress(data, 9, mtime=0))
        c.append_manifest({"source": SOURCE, "url": url, "file": os.path.relpath(path, c.ROOT).replace("\\", "/"),
                           "bytes": len(data), "sha256": c.sha256(data), "stored": "gzip", "items": n})
        print("ok", p, "items:", n, "MORE PAGES NOT FETCHED" if more else "", flush=True)
        time.sleep(1.0)


if __name__ == "__main__":
    main()
