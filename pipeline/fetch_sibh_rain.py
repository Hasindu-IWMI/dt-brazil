"""Download telemetric rain gauge records near the catchments from SP Águas' SIBH.

Source: the public JSON API behind SP Águas' SIBH portal
(https://cth.daee.sp.gov.br/sibh/), no login. SIBH gathers telemetric stations
of several operators: SP Águas, Sabesp, CEMADEN, SAISP/FCTH and IAC. Records
are 10-minute (or, for CEMADEN when dry, hourly) readings in UTC; this script
asks the API for HOURLY sums (group_type=hour), one request per station and
calendar year. Each hourly row carries `qtd`, the number of readings summed.

Selection (fixed here, applied to SIBH's own station list):
  - station type "Pluviométrico", within RADIUS_KM (the radius forcing.py
    uses) of the Cachoeira or Atibainha catchment centroid;
  - not owned by ANA: ANA's gauges are already taken from ANA's own service;
  - not a radar product ("Radar" in the name): those are areal estimates,
    not gauges;
  - not one of SIBH's conventional gauges (those SIBH lists as having
    historical daily tables); they duplicate ANA's conventional records.

Raw responses are stored exactly as received, gzip-compressed, in
data/raw/sibh/, and logged in data/raw/manifest.jsonl with the URL and the
SHA-256 of the uncompressed bytes. Station-years that return no rows are
listed in data/raw/sibh/empty_years.json so they are not asked again.

The fetch is resumable: years already on disk are skipped. --refresh
re-fetches the current and previous calendar year (and re-asks empty ones).

Usage: python fetch_sibh_rain.py [--refresh]
Then:  python sibh_rain.py   (builds daily series; see that file)
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
from forcing import CATCHMENTS, RADIUS_KM, km  # noqa: E402

API = "https://cth.daee.sp.gov.br/sibh/api"
SOURCE = "SP Águas SIBH (public API)"
RAW_DIR = os.path.join(c.RAW, "sibh")
EMPTY_INDEX = os.path.join(RAW_DIR, "empty_years.json")
STATIONS_OUT = os.path.join(c.PROCESSED, "sibh_rain_stations.json")
FIRST_YEAR = 2000
PAUSE_S = 1.0  # between requests, to be gentle on a public service


def fetch(path, params):
    url = API + path + "?" + urllib.parse.urlencode(params, doseq=True)
    return url, c.http_get(url, timeout=300, retries=4, backoff=20)


def store(name, url, data, extra=None):
    """Keep the response exactly as received, gzip-compressed (mtime 0, so
    the stored bytes depend only on the content)."""
    path = os.path.join(RAW_DIR, name)
    c.write_bytes(path, gzip.compress(data, 9, mtime=0))
    entry = {"source": SOURCE, "url": url, "file": os.path.relpath(path, c.ROOT).replace("\\", "/"),
             "bytes": len(data), "sha256": c.sha256(data), "stored": "gzip"}
    entry.update(extra or {})
    c.append_manifest(entry)
    return path


def read_raw(name):
    with gzip.open(os.path.join(RAW_DIR, name), "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def select(stations, conventional, centroids):
    """Apply the selection rules. Returns every candidate within the radius,
    with `excluded` set to the reason, or '' if it is kept."""
    out = []
    for s in stations:
        if str(s.get("station_type_id")) != "2":
            continue
        try:
            lat, lon = float(s["latitude"]), float(s["longitude"])
        except (TypeError, ValueError, KeyError):
            continue
        dists = {cat: km(cen[0], cen[1], lat, lon) for cat, cen in centroids.items()}
        if min(dists.values()) > RADIUS_KM:
            continue
        prefix = str(s.get("prefix") or "").strip()
        owner = str(s.get("station_owner") or "").strip()
        name = str(s.get("name") or "").strip()
        why = ("owned by ANA; taken from ANA's service" if owner == "ANA" else
               "radar product, not a gauge" if "radar" in name.lower() else
               "conventional gauge; duplicates ANA's record" if prefix in conventional else "")
        out.append({"id": str(s["id"]), "prefix": prefix, "owner": owner, "name": name,
                    "lat": round(lat, 5), "lon": round(lon, 5),
                    "km_to_centroid": {k: round(v, 1) for k, v in dists.items()},
                    "excluded": why})
    return sorted(out, key=lambda r: min(r["km_to_centroid"].values()))


def main():
    refresh = "--refresh" in sys.argv[1:]
    today = dt.date.today()
    cats = json.load(open(os.path.join(c.PROCESSED, "catchments.json"), encoding="utf-8"))["catchments"]
    centroids = {cat: (cats[cat]["centroid"]["lat"], cats[cat]["centroid"]["lon"]) for cat in CATCHMENTS}

    url, data = fetch("/v2/stations", {})
    store("stations.json.gz", url, data)
    url2, data2 = fetch("/v1/station_prefixes", {"pluviometricas": "true", "with_historical_measurements": "true"})
    store("conventional_rain_prefixes.json.gz", url2, data2)
    stations = json.loads(data.decode("utf-8"))
    conventional = {str(p.get("prefix") or "").strip() for p in json.loads(data2.decode("utf-8"))}
    cands = select(stations, conventional, centroids)
    kept = [s for s in cands if not s["excluded"]]
    print("SIBH rain stations within %.0f km: %d, kept %d" % (RADIUS_KM, len(cands), len(kept)), flush=True)

    empty = json.load(open(EMPTY_INDEX, encoding="utf-8")) if os.path.exists(EMPTY_INDEX) else {}
    for s in kept:
        got = 0
        for year in range(FIRST_YEAR, today.year + 1):
            key = "%s|%d" % (s["id"], year)
            name = "rain_%s_%d.json.gz" % (s["id"], year)
            recent = year >= today.year - 1
            if not (refresh and recent):
                if os.path.exists(os.path.join(RAW_DIR, name)) or key in empty:
                    continue
            params = {"format": "json", "station_prefix_ids[]": s["id"], "group_type": "hour",
                      "start_date": "%d-01-01 00:00" % year, "end_date": "%d-12-31 23:59" % year}
            try:
                url, data = fetch("/v2/measurements", params)
            except Exception as e:  # keep going; a re-run picks it up
                print("FAIL", s["id"], year, e, flush=True)
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
            time.sleep(PAUSE_S)
        c.ensure_dir(RAW_DIR)
        with open(EMPTY_INDEX, "w", encoding="utf-8") as f:
            json.dump(dict(sorted(empty.items())), f, indent=0)
        print("ok", s["id"], s["owner"], s["name"], "new hourly rows:", got, flush=True)

    with open(STATIONS_OUT, "w", encoding="utf-8") as f:
        json.dump({"source": SOURCE, "radius_km": RADIUS_KM, "retrieved": today.isoformat(),
                   "candidates": cands}, f, ensure_ascii=False, indent=1)
    print("stations:", os.path.relpath(STATIONS_OUT, c.ROOT))


if __name__ == "__main__":
    main()
