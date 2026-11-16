"""Download river, reservoir-level and transfer stations from SP Águas' SIBH.

Source: the public JSON API behind SP Águas' SIBH portal
(https://cth.daee.sp.gov.br/sibh/), no login, as for fetch_sibh_rain.py.
Records are 10-minute readings in UTC; this script asks for HOURLY means
(group_type=hour), one request per station and calendar year. Each hourly
row carries `qtd`, the number of readings averaged.

Stations: the fixed list STATIONS below, taken from SIBH's own station list
(16 November 2026). Each has a group:
  upstream   river gauges above the reservoirs, which measure inflow
             independently of the reservoir water balance;
  below_dam  river gauges on the rio Cachoeira below Cachoeira dam;
  dam        stations at the dams and in their outlet channels;
  transfer   tunnel ends and the Paraíba do Sul transfer.
Several sites appear twice under different codes (SAISP and Sabesp, or old
and new prefixes). Both are downloaded; sibh_flow.py compares them and does
not merge them.

What the fields mean, found by probing before this script was written and
re-checked on every hour by sibh_flow.py:
  value       mean water level over the hour, in cm. At river gauges and
              tunnel ends it is stage above the gauge zero. At stations in a
              reservoir or outlet channel it is the water-surface elevation:
              Barragem Cachoeira reads 81,632 cm at 07:00 on 10 March 2024,
              and ANA's SAR gives the reservoir level as 816.32 m that day.
  read_value  mean discharge over the hour, in m3/s, which SIBH computes from
              each reading with the station's rating curve. Null where SIBH
              has no curve. At 3E-116 on 10 March 2016 the published curve
              Q = 1.0 (h - 1.0)^1.38, h in m, turns value 137.9 into 0.262,
              exactly the read_value given.

Also stored, per station: its station-prefix record
(/v1/station_prefixes/<id>, with data source and reference flows) and its
rating curves (/v1/key_curves/of_station_prefixes).

Raw responses are stored exactly as received, gzip-compressed, in
data/raw/sibh/, and logged in data/raw/manifest.jsonl with the URL and the
SHA-256 of the uncompressed bytes. Station-years that return no rows are
listed in data/raw/sibh/flow_empty_years.json so they are not asked again.

The fetch is resumable: years already on disk are skipped. --refresh
re-fetches the current and previous calendar year (and re-asks empty ones),
and the station records and rating curves.

Usage: python fetch_sibh_flow.py [--refresh]
Then:  python sibh_flow.py   (builds daily series and the report)
"""
import datetime as dt
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # isolated mode drops the script folder
import common as c  # noqa: E402
from fetch_sibh_rain import PAUSE_S, RAW_DIR, SOURCE, fetch, store  # noqa: E402

EMPTY_INDEX = os.path.join(RAW_DIR, "flow_empty_years.json")
STATIONS_OUT = os.path.join(c.PROCESSED, "sibh_flow_stations.json")
FIRST_YEAR = 2000

# SIBH station-prefix id -> (group, what the site is). Names, codes, operators
# and coordinates are taken from SIBH's station list at run time.
STATIONS = {
    "1397": ("upstream", "Rio Atibainha above Atibainha reservoir (Atibainha Montante)"),
    "1430": ("upstream", "Rio Cachoeira above Cachoeira reservoir (Cachoeira Montante)"),
    "30862": ("below_dam", "Rio Cachoeira at the Piracaia water intake, about 1 km below Cachoeira dam"),
    "832": ("below_dam", "Rio Cachoeira in Piracaia town, beside ANA gauge 62665000"),
    "10": ("dam", "Cachoeira dam"),
    "362": ("dam", "Cachoeira dam (Sabesp code SB-CA-BRC)"),
    "22": ("dam", "Cachoeira dam, downstream channel"),
    "14": ("dam", "Atibainha dam"),
    "360": ("dam", "Atibainha dam (Sabesp code SB-CA-BRA)"),
    "20": ("dam", "Atibainha dam, downstream channel"),
    "12": ("transfer", "Tunnel 6 outlet: Cachoeira to Atibainha"),
    "361": ("transfer", "Tunnel 6 outlet: Cachoeira to Atibainha (Sabesp code SB-CA-DBT6)"),
    "16": ("transfer", "Tunnel 5 intake, in Atibainha reservoir"),
    "18": ("transfer", "Tunnel 5 outlet: Atibainha to Paiva Castro (Juqueri)"),
    "349": ("transfer", "Tunnel 5 outlet: Atibainha to Paiva Castro (Sabesp code SB-CA-DBT5)"),
    "6": ("transfer", "Tunnel 7 at Jacareí dam: Jaguari-Jacareí to Cachoeira"),
    "358": ("transfer", "Tunnel 7 intake at Jacareí dam (Sabesp code SB-CA-BJC-T7)"),
    "35414": ("transfer", "Jaguari (Paraíba do Sul) to Atibainha transfer"),
    "35609": ("transfer", "Jaguari (Paraíba do Sul) to Atibainha transfer, Santa Isabel"),
    "35354": ("transfer", "Paraíba do Sul pumping station (EEAB) to Atibainha"),
    "238": ("transfer", "Paraíba do Sul pumping station (Sabesp code SB-CA-EAB-PS)"),
}


def describe(stations):
    """Station metadata from SIBH's list, for the ids in STATIONS (in that order)."""
    by_id = {str(s["id"]): s for s in stations}
    out = []
    for sid, (group, site) in STATIONS.items():
        s = by_id.get(sid)
        if s is None:
            out.append({"id": sid, "group": group, "site": site, "missing_from_list": True})
            continue
        out.append({"id": sid, "group": group, "site": site, "prefix": str(s.get("prefix") or "").strip(),
                    "alt_prefix": str(s.get("alt_prefix") or "").strip(), "station_id": str(s.get("station_id") or ""),
                    "owner": str(s.get("station_owner") or "").strip(), "name": str(s.get("name") or "").strip(),
                    "lat": round(float(s["latitude"]), 5), "lon": round(float(s["longitude"]), 5),
                    "date_last_measurement": s.get("date_last_measurement") or "",
                    "transmission_status": s.get("transmission_status") or ""})
    return out


def main():
    refresh = "--refresh" in sys.argv[1:]
    today = dt.date.today()
    url, data = fetch("/v2/stations", {})
    store("stations.json.gz", url, data)
    meta = describe(json.loads(data.decode("utf-8")))
    time.sleep(PAUSE_S)

    for s in meta:
        for kind, path, params in (("prefix", "/v1/station_prefixes/%s" % s["id"], {}),
                                   ("curves", "/v1/key_curves/of_station_prefixes", {"station_prefix_ids[]": s["id"]})):
            name = "flow_%s_%s.json.gz" % (kind, s["id"])
            if os.path.exists(os.path.join(RAW_DIR, name)) and not refresh:
                continue
            try:
                url, data = fetch(path, params)
            except Exception as e:  # keep going; a re-run picks it up
                print("FAIL", s["id"], kind, e, flush=True)
            else:
                store(name, url, data)
            time.sleep(PAUSE_S)

    empty = json.load(open(EMPTY_INDEX, encoding="utf-8")) if os.path.exists(EMPTY_INDEX) else {}
    for s in meta:
        got = 0
        for year in range(FIRST_YEAR, today.year + 1):
            key = "%s|%d" % (s["id"], year)
            name = "flow_%s_%d.json.gz" % (s["id"], year)
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
        print("ok", s["id"], s.get("prefix", ""), s.get("owner", ""), s.get("name", ""), "new hourly rows:", got, flush=True)

    with open(STATIONS_OUT, "w", encoding="utf-8") as f:
        json.dump({"source": SOURCE, "retrieved": today.isoformat(), "stations": meta}, f, ensure_ascii=False, indent=1)
    print("stations:", os.path.relpath(STATIONS_OUT, c.ROOT))


if __name__ == "__main__":
    main()
