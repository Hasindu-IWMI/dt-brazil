"""Download the two SIBH stations used by flood run 1 (docs/model_design_flood_run1.md).

Pre-run check 6 of that design: hourly flow at SP Águas' town gauge 3E-063
(Rio Atibaia, Av. São João, Atibaia) and hourly level at ANA's station
62671200 above the Salto Grande plant, for every radar pass window. Whole
calendar years from 2015 are fetched, because the dry-reference rule
(passes within 60 days of each flood pass, with 3E-063 below 240 cm) needs
the town gauge's level around each pass, not only during the flood.

SAISP code 814 at the Salto Grande site is NOT fetched: it reports the same
instrument as 62671200 and served values in another unit in September 2026
(docs/flood_option_check.md, section 4).

Same API, fields and storage as fetch_sibh_flow.py (hourly means, UTC,
`value` = level in cm, `read_value` = discharge from SIBH's rating, raw
responses gzip-compressed in data/raw/sibh/ and logged in the manifest).
Files are named flood_<id>_<year>.json.gz, so they do not mix with the
stations of fetch_sibh_flow.py. Resumable: years on disk are skipped;
--refresh re-fetches the current and previous year.

Part of run_all.py since 17 November 2026: the viewer shows the town gauge's
daily level (pipeline/flood_gauges.py), so the weekly refresh keeps it current.
Flood run 1 itself is closed; adding newer years changes none of its inputs.

Usage: python fetch_flood_stations.py [--refresh]
Then:  python flood_passes.py
"""
import datetime as dt
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
from fetch_sibh_rain import PAUSE_S, RAW_DIR, SOURCE, fetch, store  # noqa: E402

EMPTY_INDEX = os.path.join(RAW_DIR, "flood_empty_years.json")
FIRST_YEAR = 2015

# SIBH station-prefix id -> what the site is
STATIONS = {
    "30863": "3E-063, Rio Atibaia at Av. São João, Atibaia town (SP Águas): flow in, overflow level 301 cm",
    "14585": "62671200, Rio Atibaia above the Salto Grande plant (ANA): level at the downstream end",
}


def main():
    refresh = "--refresh" in sys.argv[1:]
    today = dt.date.today()
    for sid in STATIONS:
        for kind, path, params in (("prefix", "/v1/station_prefixes/%s" % sid, {}),
                                   ("station", "/v2/stations/%s" % sid, {}),
                                   ("curves", "/v1/key_curves/of_station_prefixes", {"station_prefix_ids[]": sid})):
            name = "flood_%s_%s.json.gz" % (kind, sid)
            if os.path.exists(os.path.join(RAW_DIR, name)) and not refresh:
                continue
            try:
                url, data = fetch(path, params)
            except Exception as e:  # keep going; a re-run picks it up
                print("FAIL", sid, kind, e, flush=True)
            else:
                store(name, url, data)
            time.sleep(PAUSE_S)

    empty = json.load(open(EMPTY_INDEX, encoding="utf-8")) if os.path.exists(EMPTY_INDEX) else {}
    for sid, site in STATIONS.items():
        got = 0
        for year in range(FIRST_YEAR, today.year + 1):
            key = "%s|%d" % (sid, year)
            name = "flood_%s_%d.json.gz" % (sid, year)
            recent = year >= today.year - 1
            if not (refresh and recent):
                if os.path.exists(os.path.join(RAW_DIR, name)) or key in empty:
                    continue
            params = {"format": "json", "station_prefix_ids[]": sid, "group_type": "hour",
                      "start_date": "%d-01-01 00:00" % year, "end_date": "%d-12-31 23:59" % year}
            try:
                url, data = fetch("/v2/measurements", params)
            except Exception as e:  # keep going; a re-run picks it up
                print("FAIL", sid, year, e, flush=True)
                time.sleep(PAUSE_S)
                continue
            rows = len(json.loads(data.decode("utf-8")).get("measurements") or [])
            if rows == 0:
                empty[key] = today.isoformat()
                c.append_manifest({"source": SOURCE, "url": url, "file": None, "bytes": len(data),
                                   "sha256": c.sha256(data), "rows": 0})
            else:
                empty.pop(key, None)
                store(name, url, data, {"rows": rows})
                got += rows
            print("  ", sid, year, "rows:", rows, flush=True)
            time.sleep(PAUSE_S)
        c.ensure_dir(RAW_DIR)
        with open(EMPTY_INDEX, "w", encoding="utf-8") as f:
            json.dump(dict(sorted(empty.items())), f, indent=0)
        print("ok", sid, site, "new hourly rows:", got, flush=True)


if __name__ == "__main__":
    main()
